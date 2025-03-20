import socket
import os  # pour gérer les fichiers et dossiers
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
    print("ACK final envoyé avec succès, handshake réussi")

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
        nom_fichier = commande.split(" ")[1]  # Extraction du nom du fichier demandé
        client_udp.sendto(f"get|{nom_fichier}".encode('utf-8'), adresse_serveur)

        # Reception du hash SHA-256 du fichier depuis le serveur
        hash_recu, _ = client_udp.recvfrom(4096)
        hash_recu = hash_recu.decode('utf-8')
        print(f"Hash SHA-256 reçu du serveur : {hash_recu}")

        # Verifier si le serveur indique que le fichier est introuvable
        try:
            premier_segment, _ = client_udp.recvfrom(4096)
            if premier_segment.decode('utf-8') == "Erreur! : Fichier introuvable.":
                print(" Le serveur a indique que le fichier est introuvable.")
                continue  # Retourner a la boucle sans fermer le client

        except socket.timeout:
            print(" Timeout ! Le serveur ne repond pas.")
            continue  # Retourner à la boucle sans fermer le client

        # Verifier et creer le dossier `fichiers_recus` s'il n'existe pas
        if not os.path.exists("fichiers_recus"):
            os.makedirs("fichiers_recus")

        # Réception et sauvegarde du fichier
        chemin_sauvegarde = f"fichiers_recus/{nom_fichier}"

        with open(chemin_sauvegarde, "wb") as fichier_recu:
            while True:
                try:
                    client_udp.settimeout(3.0)  # Timeout pour eviter un blocage infini
                    segment, _ = client_udp.recvfrom(1024)  # Recuperation d'un segment 

                    if segment == b"FIN":  # Fin du fichier donc fin du transfert
                        print(" Telechargement termine !")
                        break

                    hash_calcule = calculer_sha256(chemin_sauvegarde)

                    #  Verification de l'intégrite du fichier
                    if hash_calcule == hash_recu:
                        print("Verification reussie : le fichier est intact.")
                    else:
                       print(" Erreur : le fichier est corrompu !")
                       print(f"Hash attendu : {hash_recu}")
                       print(f"Hash obtenu  : {hash_calcule}")

                    fichier_recu.write(segment)  # Écriture du segment reçu
                    client_udp.sendto("ACK".encode('utf-8'), adresse_serveur)  # Envoi de l'acquittement

                except socket.timeout:
                    print(" Timeout ! Le serveur ne repond pas... Nouveau essai en cours.")

        print(f" Fichier `{nom_fichier}` telecharge avec succes dans `fichiers_recus/`")
