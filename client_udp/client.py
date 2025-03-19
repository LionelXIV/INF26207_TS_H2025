import socket

client_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
adresse_serveur = ("127.0.0.1", 2212)

client_udp.sendto("SYN".encode('utf-8'), adresse_serveur)

reponse, _ = client_udp.recvfrom(4096)
reponse = reponse.decode('utf-8')

print(f"réponse reçue du serveur: {reponse}")

#  on récupère les 3 parties
commande, taille_bloc, nbr_bloc_ack = reponse.split("|")

if commande == "SYN-ACK":
    print(f"taille bloc : {taille_bloc}, nombre bloc avant ACK : {nbr_bloc_ack}")
    client_udp.sendto("ACK".encode('utf-8'), adresse_serveur)
    print("ACK final envoyé avec succès, handshake réussi")

# Demande de la liste des fichiers au serveur 
client_udp.sendto("ls".encode('utf-8'), adresse_serveur)

# Reception de la liste des fichiers demandee
reponse, _ = client_udp.recvfrom(4096)
print(f"Fichiers disponibles sur le serveur : {reponse.decode('utf-8')}")

# Demande d'un fichier specifique
nom_fichier = input("Veuillez entrer le nom du fichier a telecharger :")
client_udp.sendto(f"get|{nom_fichier}".encode('utf-8'), adresse_serveur)

# Reception et sauvegarde du fichier
chemin_sauvegarde = f"fichiers_recus/{nom_fichier}"

with open(chemin_sauvegarde, "wb") as fichier_recu:
    while True:
        segment, _ = client_udp.recvfrom(1024) # Recuparation d'un segment 

        if segment == b"FIN": # Fin du fichier donc fin du transfere
            print("Telechargement terminer !")
            break

        fichier_recu.write(segment) # Ecriture du segment recu
        client_udp.sendto("ACK".encode('utf-8'), adresse_serveur) # Envoie de l'acquittement 

client_udp.close()

