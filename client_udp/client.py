import socket
import os  # pour gérer les fichiers et dossiers

client_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
adresse_serveur = ("127.0.0.1", 2212)

client_udp.sendto("SYN".encode('utf-8'), adresse_serveur)

reponse, _ = client_udp.recvfrom(4096)
reponse = reponse.decode('utf-8')

print(f"reponse recue du serveur: {reponse}")

#  on recupere les 3 parties
commande, taille_bloc, nbr_bloc_ack = reponse.split("|")

if commande == "SYN-ACK":
    print(f"taille bloc : {taille_bloc}, nombre bloc avant ACK : {nbr_bloc_ack}")
    client_udp.sendto("ACK".encode('utf-8'), adresse_serveur)
    print("ACK final envoyé avec succès, handshake réussi")

# Demande de la liste des fichiers au serveur 
client_udp.sendto("ls".encode('utf-8'), adresse_serveur)

# Reception de la liste des fichiers demandée
reponse, _ = client_udp.recvfrom(4096)
print(f"Fichiers disponibles sur le serveur : {reponse.decode('utf-8')}")

# Demande d'un fichier spécifique
nom_fichier = input("Veuillez entrer le nom du fichier a telecharger :")
client_udp.sendto(f"get|{nom_fichier}".encode('utf-8'), adresse_serveur)

# Verifier si le serveur indique que le fichier est introuvable
try:
    premier_segment, _ = client_udp.recvfrom(4096)
    if premier_segment.decode('utf-8') == "Erreur! : Fichier introuvable.":
        print(" Le serveur a indique que le fichier est introuvable.")
        client_udp.close()
        exit()  # On quitte le programme proprement

except socket.timeout:
    print("⏳ Timeout ! Le serveur ne repond pas.")
    client_udp.close()
    exit()

# Verifier et creer le dossier fichiers_recus s'il n'existe pas
if not os.path.exists("fichiers_recus"):
    os.makedirs("fichiers_recus")

# Reception et sauvegarde du fichier
chemin_sauvegarde = f"fichiers_recus/{nom_fichier}"

with open(chemin_sauvegarde, "wb") as fichier_recu:
    while True:
        try:
            client_udp.settimeout(3.0)  # Timeout pour eviter un blocage infini
            segment, _ = client_udp.recvfrom(1024)  # Recuperation d'un segment 

            if segment == b"FIN":  # Fin du fichier donc fin du transfert
                print(" Telechargement termine !")
                break

            fichier_recu.write(segment)  # Écriture du segment reçu
            client_udp.sendto("ACK".encode('utf-8'), adresse_serveur)  # Envoi de l'acquittement

        except socket.timeout:
            print(" Timeout ! Le serveur ne repond pas...  nouveau essaie en cours.")

client_udp.close()

