DAVINCI SPEED EDITOR FOR PREMIERE PRO 1.1.0
================================================

Compatibilita: Windows 10/11, Premiere Pro 2025-2027, USB-C e Bluetooth.

INSTALLAZIONE
1. Chiudi Premiere Pro e DaVinci Resolve.
2. Collega la Speed Editor via USB-C oppure abbinala in Bluetooth a Windows.
3. Fai doppio clic su Install-SpeedEditor.cmd e conferma la richiesta amministratore.
4. Apri Premiere Pro.
5. Vai in Modifica > Preferenze > Superficie di controllo > Aggiungi.
6. Scegli DaVinci Speed Editor.

PANNELLO DI CONFIGURAZIONE
Apri Finestra > UXP Plugins > Speed Editor.
Il pannello regola la velocita della Jog e mappa pressione singola/doppia di ogni
tasto su un comando nativo di Premiere, una scorciatoia o Nessuna azione.

AGGIORNAMENTI
Esegui di nuovo l'installer. Il file personale premiere_mapping.json viene
conservato. Il bridge ricarica le modifiche senza essere riavviato.

DISINSTALLAZIONE
Esegui Uninstall-SpeedEditor.ps1 da PowerShell come amministratore.
Per eliminare anche le impostazioni usa: .\Uninstall-SpeedEditor.ps1 -RemoveSettings

NOTE
- DaVinci Resolve deve essere chiuso: il dispositivo HID puo essere usato da un
  solo programma alla volta.
- Se il Bluetooth e in sospensione, premi un tasto sulla Speed Editor per
  risvegliarla. Il bridge tenta automaticamente la riconnessione.
