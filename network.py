#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Network module - Transfert TCP
"""

import socket
import threading
import zlib
import os
from pathlib import Path
from typing import Callable, Optional

# ============================================================================
# CONSTANTES
# ============================================================================
BUFFER_SIZE = 64 * 1024  # 64 Ko
DEFAULT_PORT = 5000
DEFAULT_IP = "127.0.0.1"
COMPRESSION_LEVEL = 1

# ============================================================================
# CLIENT TCP
# ============================================================================
class TransfertClient:
    """Client de transfert de fichiers"""
    
    def __init__(self, log_callback: Callable, progress_callback: Optional[Callable] = None):
        self.log = log_callback
        self.progress = progress_callback
        self.socket = None
        self.connecte = False
        self.cancel = False
        self.socket_lock = threading.Lock()
        self.total_bytes_sent = 0

    def connecter(self, ip: str, port: int) -> bool:
        if self.connecte:
            self.log("⚠️ Déjà connecté.")
            return True

        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.socket.settimeout(30)
            self.socket.connect((ip, port))
            self.connecte = True
            self.log(f"✅ Connecté à {ip}:{port}")
            return True
        except Exception as e:
            self.log(f"❌ Connexion échouée: {e}")
            return False

    def envoyer_fichier(self, chemin_fichier: str):
        if not self.connecte:
            self.log("⚠️ Pas connecté.")
            return

        if not os.path.isfile(chemin_fichier):
            self.log(f"❌ Fichier introuvable: {chemin_fichier}")
            return

        nom_fichier = os.path.basename(chemin_fichier)
        taille_fichier = os.path.getsize(chemin_fichier)

        try:
            with self.socket_lock:
                self.socket.send(b'SEND')
                self.socket.send(len(nom_fichier).to_bytes(4, 'big'))
                self.socket.send(nom_fichier.encode('utf-8'))
                self.socket.send(taille_fichier.to_bytes(8, 'big'))

            envoye = 0
            buffer_count = 0

            with open(chemin_fichier, 'rb') as f:
                while True:
                    if self.cancel:
                        return

                    chunk = f.read(BUFFER_SIZE)
                    if not chunk:
                        break

                    if COMPRESSION_LEVEL > 0:
                        chunk = zlib.compress(chunk, COMPRESSION_LEVEL)

                    with self.socket_lock:
                        self.socket.send(chunk)

                    envoye += len(chunk)
                    buffer_count += 1

                    if self.progress and taille_fichier > 0:
                        pourcentage = (envoye / taille_fichier) * 100
                        self.progress(
                            f"📤 {nom_fichier} | {pourcentage:.1f}% | Buffer {buffer_count}",
                            pourcentage
                        )

            with self.socket_lock:
                try:
                    reponse = self.socket.recv(2)
                    if reponse == b'OK':
                        self.log(f"✅ {nom_fichier} envoyé")
                    else:
                        self.log(f"❌ Échec: {nom_fichier}")
                except:
                    self.log(f"⚠️ Pas de confirmation pour {nom_fichier}")

        except Exception as e:
            self.log(f"❌ Erreur: {e}")

    def recevoir_fichier(self, nom_fichier: str):
        if not self.connecte:
            self.log("⚠️ Pas connecté.")
            return

        try:
            with self.socket_lock:
                self.socket.send(b'RECV')
                self.socket.send(len(nom_fichier).to_bytes(4, 'big'))
                self.socket.send(nom_fichier.encode('utf-8'))

                reponse = self.socket.recv(8)
                if reponse == b'ERROR':
                    self.log("❌ Fichier non trouvé sur le serveur.")
                    return

                taille_fichier = int.from_bytes(reponse, 'big')

            dossier_client = "recus_client"
            Path(dossier_client).mkdir(exist_ok=True)
            chemin = os.path.join(dossier_client, nom_fichier)

            recu = 0
            with open(chemin, 'wb') as f:
                while recu < taille_fichier:
                    if self.cancel:
                        return

                    a_lire = min(BUFFER_SIZE, taille_fichier - recu)
                    with self.socket_lock:
                        data = self.socket.recv(a_lire)
                    if not data:
                        break

                    try:
                        data = zlib.decompress(data)
                    except:
                        pass

                    f.write(data)
                    recu += len(data)

                    if self.progress:
                        pourcentage = (recu / taille_fichier) * 100
                        self.progress(f"📥 {nom_fichier} | {pourcentage:.1f}%", pourcentage)

            with self.socket_lock:
                self.socket.send(b'OK')

            self.log(f"✅ Fichier reçu: {nom_fichier}")

        except Exception as e:
            self.log(f"❌ Erreur réception: {e}")

    def deconnecter(self):
        self.cancel = True
        if self.socket:
            try:
                self.socket.send(b'QUIT')
            except:
                pass
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        self.connecte = False
        self.log("✅ Déconnecté")


# ============================================================================
# SERVEUR TCP
# ============================================================================
class ServeurTCP:
    """Serveur TCP"""
    
    def __init__(self, log_callback: Callable, progress_callback: Optional[Callable] = None):
        self.log = log_callback
        self.progress = progress_callback
        self.socket_ecoute = None
        self.en_cours = False
        self.dossier_reception = "recus"
        self.port = DEFAULT_PORT

    def demarrer(self, port: int, dossier: str):
        if self.en_cours:
            self.log("⚠️ Serveur déjà en cours.")
            return

        self.port = port
        self.dossier_reception = dossier

        try:
            Path(self.dossier_reception).mkdir(exist_ok=True)
        except Exception as e:
            self.log(f"❌ Erreur création dossier: {e}")
            return

        try:
            self.socket_ecoute = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket_ecoute.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket_ecoute.bind(('0.0.0.0', self.port))
            self.socket_ecoute.listen(5)
        except Exception as e:
            self.log(f"❌ Erreur bind: {e}")
            return

        self.en_cours = True
        self.log(f"✅ Serveur démarré sur le port {self.port}")
        self.log(f"📁 Dossier: {os.path.abspath(self.dossier_reception)}")

        thread_accept = threading.Thread(target=self._accepter_connexions, daemon=True)
        thread_accept.start()

    def _accepter_connexions(self):
        while self.en_cours:
            try:
                client_socket, addr = self.socket_ecoute.accept()
                self.log(f"📡 Client connecté: {addr[0]}:{addr[1]}")
                thread_client = threading.Thread(
                    target=self._gerer_client,
                    args=(client_socket, addr),
                    daemon=True
                )
                thread_client.start()
            except Exception as e:
                if self.en_cours:
                    self.log(f"Erreur accept: {e}")

    def _gerer_client(self, client_socket, addr):
        try:
            while True:
                commande_bytes = client_socket.recv(4)
                if not commande_bytes:
                    break
                commande = commande_bytes.decode('utf-8')

                if commande == 'SEND':
                    self._recevoir_fichier(client_socket, addr)
                elif commande == 'RECV':
                    self._envoyer_fichier(client_socket, addr)
                elif commande == 'QUIT':
                    break
                else:
                    client_socket.send(b'ERROR')
        except Exception as e:
            self.log(f"Erreur client {addr}: {e}")
        finally:
            client_socket.close()
            self.log(f"👋 Client déconnecté: {addr[0]}:{addr[1]}")

    def _recevoir_fichier(self, client_socket, addr):
        try:
            nom_len_bytes = client_socket.recv(4)
            if not nom_len_bytes:
                return
            nom_len = int.from_bytes(nom_len_bytes, 'big')
            nom_fichier = client_socket.recv(nom_len).decode('utf-8')

            taille_bytes = client_socket.recv(8)
            if not taille_bytes:
                return
            taille_fichier = int.from_bytes(taille_bytes, 'big')

            chemin = os.path.join(self.dossier_reception, nom_fichier)
            os.makedirs(os.path.dirname(chemin), exist_ok=True)

            recu = 0
            with open(chemin, 'wb') as f:
                while recu < taille_fichier:
                    a_lire = min(BUFFER_SIZE, taille_fichier - recu)
                    data = client_socket.recv(a_lire)
                    if not data:
                        break

                    try:
                        data = zlib.decompress(data)
                    except:
                        pass

                    f.write(data)
                    recu += len(data)

                    if self.progress:
                        pourcentage = (recu / taille_fichier) * 100
                        self.progress(f"📥 Réception: {nom_fichier} | {pourcentage:.1f}%", pourcentage)

            client_socket.send(b'OK')
            self.log(f"✅ Fichier reçu: {nom_fichier} ({recu} octets)")

        except Exception as e:
            self.log(f"❌ Erreur réception: {e}")
            client_socket.send(b'ERROR')

    def _envoyer_fichier(self, client_socket, addr):
        try:
            nom_len_bytes = client_socket.recv(4)
            if not nom_len_bytes:
                return
            nom_len = int.from_bytes(nom_len_bytes, 'big')
            nom_fichier = client_socket.recv(nom_len).decode('utf-8')

            chemin = os.path.join(self.dossier_reception, nom_fichier)
            if not os.path.isfile(chemin):
                client_socket.send(b'ERROR')
                self.log(f"❌ Fichier non trouvé: {nom_fichier}")
                return

            taille_fichier = os.path.getsize(chemin)
            client_socket.send(taille_fichier.to_bytes(8, 'big'))

            envoye = 0
            with open(chemin, 'rb') as f:
                while True:
                    chunk = f.read(BUFFER_SIZE)
                    if not chunk:
                        break

                    if COMPRESSION_LEVEL > 0:
                        chunk = zlib.compress(chunk, COMPRESSION_LEVEL)

                    client_socket.send(chunk)
                    envoye += len(chunk)

                    if self.progress:
                        pourcentage = (envoye / taille_fichier) * 100
                        self.progress(f"📤 Envoi: {nom_fichier} | {pourcentage:.1f}%", pourcentage)

            self.log(f"✅ Fichier envoyé: {nom_fichier}")

        except Exception as e:
            self.log(f"❌ Erreur envoi: {e}")

    def arreter(self):
        self.en_cours = False
        if self.socket_ecoute:
            try:
                self.socket_ecoute.close()
            except:
                pass
        self.log("🛑 Serveur arrêté.")
