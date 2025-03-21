# mon serveur 
import os
import socket  # importation de la bibliotheque socket pour utiliser les fonctions reseau
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
    "Calcule le hash SHA-256 d'un fichier"
    hasher = hashlib.sha256()
    with open(chemin_fichier, "rb") as fichier:
        while chunk := fichier.read(4096):  # Lire le fichier par morceaux
            hasher.update(chunk)
    return hasher.hexdigest()

# Boucle infinie pour garder le serveur actif et en ecoute en permanence
while True:
    try:
        message, adresse_client = serveur_udp.recvfrom(4096)
        message = message.decode('utf-8')

        if message == "SYN":
            print(f"SYN recu de {adresse_client}, debut du handshake.")
            # parametre a envoyer au client
            taille_bloc = 1024  # taille maximale des blocs envoyes
            nbr_bloc_ack = 5  # nombre de blocs avant ACK

            # Envoi du SYN-ACK au client avec les parametres
            reponse = f"SYN-ACK|{taille_bloc}|{nbr_bloc_ack}"
            serveur_udp.sendto(reponse.encode('utf-8'), adresse_client)
            print("SYN-ACK envoye au client avec les parametres")

            # Mise en attente du ACK du client (final)
            message_final, _ = serveur_udp.recvfrom(4096)
            message_final = message_final.decode('utf-8')

            if message_final == "ACK":
                print("La connexion est etablie avec succes.")
            else:
                print("Handshake echoue")

        if message == "bye":
            print(f"Deconnexion de : {adresse_client}. Fermeture de la connexion.")
            serveur_udp.sendto("Deconnexion effectue".encode('utf-8'), adresse_client)
            continue  # On continue a ecouter sans fermer le serveur

        if message == "ls":
            print(f"Demande de liste des fichiers du client : {adresse_client}")

            fichiers = os.listdir("fichiers_disponibles")
            liste_fichiers = "|".join(fichiers) if fichiers else "Aucun fichier disponible"

            if random.random() >= 0.05:
                serveur_udp.sendto(liste_fichiers.encode('utf-8'), adresse_client)
                print("Liste des fichiers envoyee au client")
            else:
                print("Perte simulee pour la liste des fichiers")

        if message.startswith("get|"):
            nom_fichier = message.split("|")[1]  # recupere le nom du fichier demande
            print(f"Demande de fichier recue : {nom_fichier}")

            chemin_fichier = f"fichiers_disponibles/{nom_fichier}"

            if os.path.exists(chemin_fichier):
                print(f"Fichier trouve : {nom_fichier}")

                if os.path.getsize(chemin_fichier) == 0:
                    print("Erreur : le fichier est vide.")
                    serveur_udp.sendto("ERREUR|Fichier vide".encode('utf-8'), adresse_client)
                    continue

                hash_fichier = calculer_sha256(chemin_fichier)
                serveur_udp.sendto(hash_fichier.encode('utf-8'), adresse_client)
                print(f"Hash SHA-256 envoye au client : {hash_fichier}")

                numero_sequence = 0
                segments_envoyes = {}  # Stocker les segments pour retransmission si necessaire
                PERTE_PAQUET = 0.05

                with open(chemin_fichier, "rb") as fichier:
                    while True:
                        segment = fichier.read(1024)
                        if not segment:
                            break

                        paquet = f"{numero_sequence}|".encode('utf-8') + segment
                        segments_envoyes[numero_sequence] = paquet  # Sauvegarde pour retransmission

                        if random.random() < PERTE_PAQUET:
                            print(f"Perte simulee du paquet {numero_sequence}")
                        else:
                            serveur_udp.sendto(paquet, adresse_client)
                            print(f"Segment {numero_sequence} envoye")

                        tentatives = 0
                        while tentatives < 5:
                            try:
                                serveur_udp.settimeout(3.0)
                                ack, _ = serveur_udp.recvfrom(4096)

                                try:
                                    ack_str = ack.decode('utf-8').strip()
                                    if ack_str == f"ACK|{numero_sequence}":
                                        print(f"ACK recu pour le segment {numero_sequence}")
                                        numero_sequence += 1
                                        break
                                    else:
                                        print(f"ACK incorrect, retransmission {tentatives+1}/5")

                                except UnicodeDecodeError:
                                    print(f"ACK corrompu pour le segment {numero_sequence}, retransmission {tentatives+1}/5")

                                serveur_udp.sendto(segments_envoyes[numero_sequence], adresse_client)
                                tentatives += 1

                            except socket.timeout:
                                print(f"Timeout ! Retransmission {tentatives+1}/5")
                                serveur_udp.sendto(segments_envoyes[numero_sequence], adresse_client)
                                tentatives += 1

                        if tentatives == 5:
                            print("Echec du transfert apres 5 tentatives")
                            serveur_udp.sendto("ERREUR|Echec du transfert".encode('utf-8'), adresse_client)
                            break

                serveur_udp.sendto(f"FIN|{numero_sequence}".encode('utf-8'), adresse_client)
                print("Fichier envoye avec succes.")

                serveur_udp.settimeout(None)

            else:
                print("Fichier introuvable!")
                serveur_udp.sendto("Erreur! : Fichier introuvable.".encode('utf-8'), adresse_client)

    except ConnectionResetError:
        print("Erreur : connexion avec le client interrompue brutalement. Attente d'une nouvelle connexion...")
        continue

    except UnicodeDecodeError:
        print("Erreur de decodage d'un message recu. Ignore et attente de la prochaine requete...")
        continue
