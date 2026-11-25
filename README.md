# MB Scene Creator

Eigene Lichtszenen für Home Assistant – mit **Farbe, Farbsättigung und Helligkeit pro Lampe**.

Dieses eigenständig gepflegte Projekt von [FlorianMette91](https://github.com/FlorianMette91)
basiert auf [Scene Studio 3.7.1 von Michael Andrejews](https://github.com/andrejem/scene-studio)
und ursprünglich auf [Scene Presets von Sören Beye](https://github.com/Hypfer/hass-scene_presets).
Die Lizenz ist Apache-2.0; Herkunft und Änderungen stehen in [NOTICE](NOTICE).

## Installation über HACS

Voraussetzung: Home Assistant **2026.7 oder neuer** und HACS.

1. In HACS oben rechts **⋮ → Benutzerdefinierte Repositories** öffnen.
2. `https://github.com/FlorianMette91/MB-Scene-Creator` eintragen, Typ **Integration** wählen.
3. **MB Scene Creator** herunterladen und Home Assistant neu starten.
4. Unter **Einstellungen → Geräte & Dienste → Integration hinzufügen** nach
   **MB Scene Creator** suchen und hinzufügen.
5. **MB Scene Creator** in der Seitenleiste öffnen.

[In HACS öffnen](https://my.home-assistant.io/redirect/hacs_repository/?owner=FlorianMette91&repository=MB-Scene-Creator&category=integration)

Das Projekt ist als benutzerdefiniertes HACS-Repository installierbar. Es ist nicht
in der allgemeinen HACS-Standardliste eingetragen und kein Supervisor-Add-on.

Manuell: `custom_components/mb_scene_creator` nach `/config/custom_components/`
kopieren und anschließend Home Assistant neu starten.

## Eigene Farben pro Lampe

Im Szeneneditor unter **Lampen dieser Szene** auf **Lampenfarbe wählen** klicken.
Farbton und Sättigung oder einen Weißton einstellen. Die Helligkeit daneben separat
in Prozent wählen. **Testen** wendet die Werte an; **Speichern** behält sie dauerhaft.
**Vorlagenfarbe verwenden** entfernt die individuelle Farbwahl.

- Eine leere Helligkeit übernimmt die Szenenhelligkeit; 0 schaltet die Lampe beim Start aus.
- Eigene Farben bleiben bei dynamischen Szenen und Musik-Szenen fest.
- Sie haben Vorrang vor der globalen Farbintensität und dem Farbverlauf einer Verlaufslampe.
- Lampen mit ausschließlich Weißlicht erhalten den nächstliegenden Weißton.
- Weitere Funktionen der Basis sind vorhanden: Vorlagen, eigene Vorlagen aus Fotos,
  dynamische Szenen, optionale Lampen, Musik-Szenen und Tageszeit-Szenen.

Details: [Lampen einer Szene](docs/Lights%20of%20a%20scene.md),
[Panel](docs/Panel.md), [Dienste](docs/Services.md), [Raumkarte](docs/Room%20card.md).
Die weiterführende Dokumentation ist auf Englisch.

## Neben Scene Studio verwenden

MB Scene Creator hat eine eigene Kennung (`mb_scene_creator`), eigene Dienste,
Szenenspeicher, Browser-Einstellungen und eine eigene Raumkarte
(`custom:mb-scene-creator-room-card`). Updates von Scene Studio überschreiben dieses
Projekt nicht. Die beiden Integrationen können unabhängig installiert werden.

Bestehende Scene-Studio-Szenen und eigene Vorlagen werden **nicht automatisch übernommen**.
Zum Einstieg eine neue Testszene anlegen. Nicht gleichzeitig dynamische Szenen beider
Integrationen auf denselben Lampen starten: beide würden sonst die Lampen steuern.
Der vorhandene Importdialog betrifft das ältere **Scene Presets**, nicht Scene Studio.

## Updates und Entwicklung

Neue veröffentlichte Versionen dieses Repositorys werden über HACS angeboten.
Vor Updates ein Home-Assistant-Backup erstellen. Eigene Vorlagen liegen im persistenten
Verzeichnis `userdata` der Integration.

Entwicklungsablauf und Prüfungen: [DEVELOPMENT.md](DEVELOPMENT.md).
Fehler oder Wünsche: [Issues](https://github.com/FlorianMette91/MB-Scene-Creator/issues).

Die erste Version wurde automatisiert geprüft; Tests mit realen Lampen und deiner
Home-Assistant-Installation stehen noch aus.
