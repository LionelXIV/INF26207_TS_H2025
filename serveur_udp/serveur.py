# mon serveur 
import os
import socket # importation de la biblioteque socket pour utiliser les fonctions reseau

# creation du socket UDP IPv4
serveur_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Adresse IP locale et port ou le serveur ecoute
adresse_serveur = ("127.0.0.1", 2212)

# Liaison du socket a l'adresse IP et au port choisis
serveur_udp.bind(adresse_serveur)

print("Serveur en ecoute sur le port 2212")

# Boucle infinie pour garder le serveur actif et en ecoute en permanence
while True:
    message, adresse_client = serveur_udp.recvfrom(4096)
    message = message.decode('utf-8')

    if message == "SYN":
        print(f"SYN recu de {adresse_client}, debut du handshake.")
        # parametre a envoyer au client
        taille_bloc = 1024 #taille maximale des blocs envoyes
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

    if message == "ls":
        print(f"demande de liste des fichier du client : {adresse_client}")

        # Recuperation de la liste des fichiers disponibles dans le dossier "fichiers_disponibles"
        fichiers = os.listdir("fichiers_disponibles")
        liste_fichiers = "|".join(fichiers) if fichiers else "Aucun fichier disponible"

        # Envoyer la liste des fichiers au client
        serveur_udp.sendto(liste_fichiers.encode('utf-8'), adresse_client)
        print("Liste des fichiers envoyee au client")
    
    if message.startswith("get|"):
        nom_fichier = message.split("|")[1] # recupere le nom du fichier demande
        print(f"Demande de fichier recu : {nom_fichier}")

        chemin_fichier = f"fichiers_disponibles/{nom_fichier}"

        if os.path.exists(chemin_fichier):
            print(f"fichier trouve : {nom_fichier}")
            
            # Lire le fichier de facon binaire et transfere par paquets
            with open(chemin_fichier, "rb") as fichier:
                while True:
                    # Lecture d'un segment de 1024 octets
                    segment = fichier.read(1024)
                    if not segment:
                        break # Fin du fichier

                    serveur_udp.sendto(segment, adresse_client) # Envoie du segment

                    # Attente de l'acquitement du client (ACK)
                    ack, _ = serveur_udp.recvfrom(4096)
                    if ack.decode('utf-8') != "ACK":
                        print("Erreur! : Acquittement non recu de la part du client")
                        break 

                    # message indiquant la fin du fichier
                    serveur_udp.sendto("FIN".encode('utf8'), adresse_client)
                    print("Fichier envoye avec succes.")
        else:
            print("Fichier introuvable!")
            serveur_udp.sento("Erreur! : Fichier introuvable.".encode('utf-8'), adresse_client)
    

    