import socket
import os  # pour gerer les fichiers et dossiers
import hashlib

client_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
adresse_serveur = ("127.0.0.1", 2212)

client_udp.sendto("SYN".encode('utf-8'), adresse_serveur)

reponse, _ = client_udp.recvfrom(4096)
reponse = reponse.decode('utf-8')

print(f"Reponse recue du serveur: {reponse}")

#  On recupere les 3 parties
commande, taille_bloc, nbr_bloc_ack = reponse.split("|")

if commande == "SYN-ACK":
    print(f"Taille bloc : {taille_bloc}, Nombre bloc avant ACK : {nbr_bloc_ack}")
    client_udp.sendto("ACK".encode('utf-8'), adresse_serveur)
    print("ACK final envoye avec succes, handshake reussi")

def calculer_sha256(chemin_fichier):
    "Calcule le hash SHA-256 d'un fichier"
    hasher = hashlib.sha256()
    with open(chemin_fichier, "rb") as fichier:
        while chunk := fichier.read(4096):  # Lire le fichier par morceaux
            hasher.update(chunk)
    return hasher.hexdigest()

# Boucle pour permettre à l'utilisateur de choisir une commande
while True:
    commande = input("Veuillez entrer une commande (`ls`, `get nom_fichier`, `bye`) : ")
    client_udp.sendto(commande.encode('utf-8'), adresse_serveur)

    if commande == "bye":
        reponse, _ = client_udp.recvfrom(4096)
        print(f"Reponse du serveur : {reponse.decode('utf-8')}")
        print("Deconnexion reussie.")
        client_udp.close()
        exit()

    elif commande == "ls":
        # Recevoir la liste des fichiers disponibles
        reponse, _ = client_udp.recvfrom(4096)
        print(f"Fichiers disponibles sur le serveur : {reponse.decode('utf-8')}")

    elif commande.startswith("get "):
        nom_fichier = commande.split(" ")[1]  # Extraction du nom du fichier demande
        client_udp.sendto(f"get|{nom_fichier}".encode('utf-8'), adresse_serveur)

        # Reception du hash SHA-256 du fichier depuis le serveur
        hash_recu, _ = client_udp.recvfrom(4096)
        hash_recu = hash_recu.decode('utf-8')
        print(f"Hash SHA-256 reçu du serveur : {hash_recu}")

        # Verifier si le serveur indique que le fichier est introuvable
        try:
            premier_segment, _ = client_udp.recvfrom(4096)
            try:
                if premier_segment.decode('utf-8') == "Erreur! : Fichier introuvable.":
                    print(" Le serveur a indique que le fichier est introuvable.")
                    continue  # Retourner a la boucle sans fermer le client
            except UnicodeDecodeError:
                pass  # Le segment n'est pas du texte, donc on continue le transfert

        except socket.timeout:
            print(" Timeout ! Le serveur ne repond pas.")
            continue  # Retourner à la boucle sans fermer le client

        # Verifier et creer le dossier `fichiers_recus` s'il n'existe pas
        if not os.path.exists("fichiers_recus"):
            os.makedirs("fichiers_recus")

        # Stocker les segments recus pour une reconstruction correcte du fichier
        segments_recus = {}  # Dictionnaire pour stocker les segments recus
        dernier_numero_recu = -1  # Pour eviter les doublons

        while True:
            try:
                client_udp.settimeout(3.0)  # Timeout pour eviter un blocage infini
                segment, _ = client_udp.recvfrom(1030)  # 1024 + 6 pour le numero

                # Vérifier si on a reçu le message de fin
                if segment.startswith(b"FIN|"):
                    print("Téléchargement terminé !")
                    break

                # Extraire le numéro de sequence et les donnees du fichier
                if b"|" not in segment:
                    print(f"Erreur de format : {segment}")
                    continue  # Ignorer ce segment

                numero_recu, segment_donnees = segment.split(b"|", 1)
                try:
                    numero_recu = int(numero_recu.decode('utf-8').strip())
                except ValueError:
                    print(f"Erreur de conversion du numero de séquence : {numero_recu}")
                    continue  # Ignorer ce segment

                # Vérifier si le segment est un doublon
                if numero_recu in segments_recus:
                    print(f"Segment {numero_recu} deja recu, ignore.")
                    continue

                # Stocker le segment reçu
                segments_recus[numero_recu] = segment_donnees

                # Envoi de l'ACK correspondant avec le numero du segment
                ack_message = f"ACK|{numero_recu}"
                client_udp.sendto(ack_message.encode('utf-8'), adresse_serveur)

            except socket.timeout:
                print(" Timeout ! Le serveur ne repond pas... Nouveau essai en cours.")

        # Reconstruction du fichier en respectant l'ordre des segments
        chemin_sauvegarde = f"fichiers_recus/{nom_fichier}"
        with open(chemin_sauvegarde, "wb") as fichier_recu:
            for i in sorted(segments_recus.keys()):
                fichier_recu.write(segments_recus[i])

        # Verification finale du hash SHA-256
        hash_calcule = calculer_sha256(chemin_sauvegarde)

        if hash_calcule == hash_recu:
            print("Verification reussie : Le fichier est intact.")
        else:
            print("Erreur : Le fichier est corrompu !")
            print(f"Hash attendu : {hash_recu}")
            print(f"Hash obtenu  : {hash_calcule}")

        print(f"Fichier `{nom_fichier}` telecharge avec succes dans `fichiers_recus/`")
