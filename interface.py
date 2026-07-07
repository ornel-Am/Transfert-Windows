#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interface Kivy - Universelle
"""

import os
import threading
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.progressbar import ProgressBar
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.utils import platform

from network import TransfertClient, ServeurTCP, DEFAULT_IP, DEFAULT_PORT, BUFFER_SIZE

# ============================================================================
# ÉCRAN PRINCIPAL
# ============================================================================
class TransfertScreen(BoxLayout):
    """Écran principal universel"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Variables
        self.mode = "client"
        self.client = None
        self.serveur = None
        self.connecte = False
        self.fichier_a_envoyer = None
        
        # Construire l'interface
        self._creer_widgets()
        self._afficher_infos()
        self.log("✅ Application Transfert Universelle")
        
        # Demander les permissions Android
        if platform == 'android':
            self._demander_permissions_android()

    def _demander_permissions_android(self):
        """Demande les permissions pour Android"""
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.INTERNET
            ])
        except:
            pass

    def _creer_widgets(self):
        """Crée l'interface universelle"""
        self.orientation = 'vertical'
        self.spacing = 8
        self.padding = 10
        
        # Header
        header = BoxLayout(size_hint_y=0.07)
        header.add_widget(Label(text=f"Transfert TCP ({platform})", font_size='18sp', bold=True))
        self.add_widget(header)
        
        # Mode
        mode_layout = BoxLayout(size_hint_y=0.07)
        self.btn_client = Button(text="🖥️ Client")
        self.btn_client.bind(on_press=self._set_mode_client)
        self.btn_serveur = Button(text="📡 Serveur")
        self.btn_serveur.bind(on_press=self._set_mode_serveur)
        mode_layout.add_widget(self.btn_client)
        mode_layout.add_widget(self.btn_serveur)
        self.add_widget(mode_layout)
        
        # Configuration
        config_layout = BoxLayout(size_hint_y=0.12, orientation='vertical')
        
        ip_port = BoxLayout(size_hint_y=0.5)
        self.ip_input = TextInput(text=DEFAULT_IP, hint_text="IP", multiline=False)
        self.port_input = TextInput(text=str(DEFAULT_PORT), hint_text="Port", multiline=False, input_filter='int')
        ip_port.add_widget(self.ip_input)
        ip_port.add_widget(self.port_input)
        config_layout.add_widget(ip_port)
        
        self.btn_connect = Button(text="🔌 Connecter", size_hint_y=0.5, background_color=(0.2, 0.6, 0.2, 1))
        self.btn_connect.bind(on_press=self._action_connect)
        config_layout.add_widget(self.btn_connect)
        self.add_widget(config_layout)
        
        # Actions
        action_layout = BoxLayout(size_hint_y=0.07)
        self.btn_choisir = Button(text="📄 Fichier")
        self.btn_choisir.bind(on_press=self._choisir_fichier)
        self.btn_envoyer = Button(text="🚀 Envoyer")
        self.btn_envoyer.bind(on_press=self._action_envoyer)
        action_layout.add_widget(self.btn_choisir)
        action_layout.add_widget(self.btn_envoyer)
        self.add_widget(action_layout)
        
        # Progression
        progress_layout = BoxLayout(size_hint_y=0.15, orientation='vertical')
        self.progress_label = Label(text="En attente...", text_size=(Window.width, None), halign='center')
        self.progress_bar = ProgressBar(max=100, value=0)
        progress_layout.add_widget(self.progress_label)
        progress_layout.add_widget(self.progress_bar)
        self.add_widget(progress_layout)
        
        # Logs
        log_layout = BoxLayout(orientation='vertical')
        log_label = Label(text="📋 Logs", size_hint_y=0.05)
        self.log_text = TextInput(
            multiline=True,
            readonly=True,
            background_color=(0.05, 0.05, 0.05, 1),
            foreground_color=(0.8, 0.8, 0.8, 1),
            font_size='11sp'
        )
        log_layout.add_widget(log_label)
        log_layout.add_widget(self.log_text)
        self.add_widget(log_layout)

    def _set_mode_client(self, instance):
        self.mode = "client"
        self.btn_client.background_color = (0.2, 0.6, 0.2, 1)
        self.btn_serveur.background_color = (1, 1, 1, 1)
        self.btn_connect.text = "🔌 Connecter"
        self.ip_input.text = DEFAULT_IP
        self.ip_input.disabled = False
        self.btn_choisir.disabled = False
        self.btn_envoyer.disabled = True
        self.log("🔄 Mode Client")

    def _set_mode_serveur(self, instance):
        self.mode = "serveur"
        self.btn_serveur.background_color = (0.2, 0.6, 0.2, 1)
        self.btn_client.background_color = (1, 1, 1, 1)
        self.btn_connect.text = "▶️ Démarrer"
        self.ip_input.text = "0.0.0.0"
        self.ip_input.disabled = True
        self.btn_choisir.disabled = True
        self.btn_envoyer.disabled = True
        self.log("🔄 Mode Serveur")

    def _action_connect(self, instance):
        if self.mode == "client":
            ip = self.ip_input.text
            try:
                port = int(self.port_input.text)
            except ValueError:
                self.log("❌ Port invalide")
                return
            
            self.client = TransfertClient(self.log, self.update_progress)
            if self.client.connecter(ip, port):
                self.connecte = True
                self.btn_connect.text = "✅ Connecté"
                self.btn_envoyer.disabled = False
                self.btn_choisir.disabled = False
        else:
            try:
                port = int(self.port_input.text)
            except ValueError:
                self.log("❌ Port invalide")
                return
            
            dossier = "recus"
            self.serveur = ServeurTCP(self.log, self.update_progress)
            self.serveur.demarrer(port, dossier)
            if self.serveur.en_cours:
                self.connecte = True
                self.btn_connect.text = "✅ Démarré"

    def _choisir_fichier(self, instance):
        """Sélecteur de fichiers universel"""
        content = BoxLayout(orientation='vertical')
        filechooser = FileChooserListView()
        
        btn_layout = BoxLayout(size_hint_y=0.12)
        btn_annuler = Button(text="Annuler")
        btn_valider = Button(text="Valider")
        btn_layout.add_widget(btn_annuler)
        btn_layout.add_widget(btn_valider)
        
        content.add_widget(filechooser)
        content.add_widget(btn_layout)
        
        popup = Popup(
            title="Choisir un fichier",
            content=content,
            size_hint=(0.9, 0.9)
        )
        
        def valider(instance):
            if filechooser.selection:
                self.fichier_a_envoyer = filechooser.selection[0]
                self.log(f"📄 Sélectionné: {os.path.basename(self.fichier_a_envoyer)}")
                self.btn_envoyer.disabled = False
                popup.dismiss()
        
        def annuler(instance):
            popup.dismiss()
        
        btn_valider.bind(on_press=valider)
        btn_annuler.bind(on_press=annuler)
        popup.open()

    def _action_envoyer(self, instance):
        if not self.fichier_a_envoyer:
            self.log("⚠️ Aucun fichier sélectionné")
            return
        
        if not self.client or not self.client.connecte:
            self.log("⚠️ Client non connecté")
            return
        
        self.btn_envoyer.disabled = True
        self.btn_choisir.disabled = True
        
        threading.Thread(
            target=self.client.envoyer_fichier,
            args=(self.fichier_a_envoyer,),
            daemon=True
        ).start()
        
        Clock.schedule_once(self._reactiver_boutons, 2)

    def _reactiver_boutons(self, dt):
        self.btn_envoyer.disabled = False
        self.btn_choisir.disabled = False

    def _afficher_infos(self):
        info = f"🧩 Buffer: {BUFFER_SIZE//1024} Ko | Compression: Oui"
        self.log(f"ℹ️ {info}")

    def log(self, message):
        """Ajoute un message dans les logs"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_text.text += f"[{timestamp}] {message}\n"
        self.log_text.cursor = (0, len(self.log_text.text))
        self.log_text.scroll_cursor()

    def update_progress(self, label, value):
        """Met à jour la barre de progression"""
        self.progress_label.text = label
        self.progress_bar.value = value
        Clock.unschedule(self._update_ui)
        Clock.schedule_once(self._update_ui, 0.01)

    def _update_ui(self, dt):
        self.progress_bar.value = self.progress_bar.value
