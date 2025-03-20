# mon serveur 
import os
import socket # importation de la bibliotheque socket pour utiliser les fonctions reseau
import random 
import hashlib


# creation du socket UDP IPv4
serveur_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Adresse IP locale et port ou le serveur ecoute
adresse_serveur = ("127.0.0.1", 2212)

# Liaison du socket a l'adresse IP et au port choisis
serveur_udp.bind(adresse_serveur)

print("Serveur en ecoute sur le port 2212")

def calculer_sha256(chemin_fichier):
    "calcule le hash SHA-256 d'un fichier"
    hasher = hashlib.sha256()
    with open(chemin_fichier, "rb") as fichier:
        while chunk := fichier.read(4096): # Lire le fichier par morceaux
            hasher.update(chunk)
    return hasher.hexdigest()

# Boucle infinie pour garder le serveur actif et en ecoute en permanence
while True:
    message, adresse_client = serveur_udp.recvfrom(4096)
    message = message.decode('utf-8')

    if message == "SYN":
        print(f"SYN recu de {adresse_client}, debut du handshake.")
        # parametre a envoyer au client
        taille_bloc = 1024 # taille maximale des blocs envoyés
        nbr_bloc_ack = 5 # nombre de blocs avant ACK

        # Envoi du SYN-ACK au client avec les parametres
        reponse = f"SYN-ACK|{taille_bloc}|{nbr_bloc_ack}"
        serveur_udp.sendto(reponse.encode('utf-8'), adresse_client)
        print("SYN-ACK envoye au client avec les parametres")

        # Mise en attente du ACK du client (final)
        message_final, adresse_finale = serveur_udp.recvfrom(4096)
        message_final = message_final.decode('utf-8')

        if message_final == "ACK":
            print("La connexion est etablie avec succes.")
        else:
            print("Handshake echoue")
        
    if message == "bye":
        print(f"Deconnrxion de : {adresse_client}.Fermeture de la connexion.")
        serveur_udp.sendto("Deconnexion effectue".encode('utf-8'), adresse_client)
        continue # On continue a ecouter sans fermer le serveur

    if message == "ls":
        print(f"Demande de liste des fichiers du client : {adresse_client}")

        # Recuperation de la liste des fichiers disponibles dans le dossier "fichiers_disponibles"
        fichiers = os.listdir("fichiers_disponibles")
        liste_fichiers = "|".join(fichiers) if fichiers else "Aucun fichier disponible"

        # Envoyer la liste des fichiers au client
        serveur_udp.sendto(liste_fichiers.encode('utf-8'), adresse_client)
        print("Liste des fichiers envoyée au client")
    
    if message.startswith("get|"):
        nom_fichier = message.split("|")[1] # recupere le nom du fichier demandé
        print(f"Demande de fichier reçue : {nom_fichier}")

        chemin_fichier = f"fichiers_disponibles/{nom_fichier}"

        if os.path.exists(chemin_fichier):
            print(f"Fichier trouvé : {nom_fichier}")

            # Calcul du hash SHA-256 du fichier
            hash_fichier = calculer_sha256(chemin_fichier)
            
            # Envoi du hash SHA-256 au client avant d'envoyer le fichier 
            serveur_udp.sendto(hash_fichier.encode('utf-8'), adresse_client)
            print(f"Hash SHA-256 envoye au client : {hash_fichier}")
            
            # Lire le fichier de façon binaire et transférer par paquets
            with open(chemin_fichier, "rb") as fichier:
                PERTE_PAQUET = 0.05 # Pourcentage de paquet perdu (5%)
                while True:
                    # Lecture d'un segment de 1024 octets
                    segment = fichier.read(1024)
                    if not segment:
                        break # Fin du fichier

                    # Simulation de perte de paquet (5%)
                    if random.random() < PERTE_PAQUET:
                        print("Perte simulée, pas de transfert")
                        continue # On "perd" ce segment

                    # Transfert du segment au client
                    serveur_udp.sendto(segment, adresse_client)
                    print("Segment envoyé")

                    # En attente de l'acquittement du client avec un timeout de 3s 
                    tentatives = 0
                    while tentatives < 5:  # Limite de 5 tentatives
                        try:
                            serveur_udp.settimeout(3.0)  # Timeout de 3 secondes
                            ack, _ = serveur_udp.recvfrom(4096)

                            if ack.decode('utf-8') == "ACK":
                                print("ACK reçu pour ce segment")
                                break  # On passe au segment suivant si l'ACK est reçu
                            else:
                                print(f"ACK non reçu, tentative {tentatives+1}/5")
                                serveur_udp.sendto(segment, adresse_client)  # Retransmission du segment
                                tentatives += 1
                        except socket.timeout:
                            tentatives += 1
                            print(f"Timeout ! Retransmission {tentatives}/5")
                            serveur_udp.sendto(segment, adresse_client)  # Retransmission après Timeout
                    
                    if tentatives == 5:
                        print("Échec du transfert après 5 tentatives")
                        serveur_udp.sendto("Échec du transfert".encode('utf-8'), adresse_client)
                        break  # On arrête le transfert

            # Envoi de "FIN" une seule fois apres le transfert
            serveur_udp.sendto("FIN".encode('utf8'), adresse_client)
            print("Fichier envoyé avec succès.")

            # Reinitialisation du timeout 
            serveur_udp.settimeout(None)

        else:
            print("Fichier introuvable!")
            serveur_udp.sendto("Erreur! : Fichier introuvable.".encode('utf-8'), adresse_client)
