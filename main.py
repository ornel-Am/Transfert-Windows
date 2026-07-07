#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Transfert Universal - Main
Fonctionne sur Android, iOS, Windows, Linux, macOS
"""

import os
import sys

# Ajouter le chemin src
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kivy.app import App
from kivy.core.window import Window
from kivy.utils import platform
from interface import TransfertScreen


class TransfertApp(App):
    """Application principale universelle"""
    
    def build(self):
        # Configuration selon la plateforme
        if platform in ('android', 'ios'):
            Window.size = (400, 700)
        else:
            Window.size = (500, 750)
        
        Window.clearcolor = (0.1, 0.1, 0.1, 1)
        return TransfertScreen()

    def on_stop(self):
        """Nettoyer à la fermeture"""
        screen = self.root
        if hasattr(screen, 'client') and screen.client:
            screen.client.deconnecter()
        if hasattr(screen, 'serveur') and screen.serveur:
            screen.serveur.arreter()


if __name__ == '__main__':
    TransfertApp().run()
