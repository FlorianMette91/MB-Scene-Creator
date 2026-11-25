# MB Scene Creator

<img src="https://raw.githubusercontent.com/FlorianMette91/MB-Scene-Creator/main/custom_components/mb_scene_creator/brand/icon%402x.png" alt="MB Scene Creator Logo" width="160" height="160">

Eigene Lichtszenen für Home Assistant – mit **Farbe, Farbsättigung und Helligkeit pro Lampe**.

Dieses eigenständig gepflegte Projekt von [FlorianMette91](https://github.com/FlorianMette91)
basiert auf [Scene Studio 3.7.1 von Michael Andrejews](https://github.com/andrejem/scene-studio)
und ursprünglich auf [Scene Presets von Sören Beye](https://github.com/Hypfer/hass-scene_presets).
Die Lizenz ist Apache-2.0; Herkunft und Änderungen stehen in [NOTICE](NOTICE).

## Installation über den Marketplace (öffentliches Repository)

Der integrierte Marketplace ersetzt HACS seit Home Assistant 2026.11.
Die Integration selbst unterstützt Home Assistant 2026.7 oder neuer.

1. **Einstellungen → Marketplace → Aus Link hinzufügen** öffnen.
2. `https://github.com/FlorianMette91/MB-Scene-Creator` eintragen und hinzufügen.
   Falls gefragt, GitHub verbinden und den Typ **Integration** auswählen.
3. **MB Scene Creator** installieren und den angezeigten Neustart-Hinweisen folgen.
4. Unter **Einstellungen → Geräte & Dienste → Integration hinzufügen** nach
   **MB Scene Creator** suchen und hinzufügen.
5. **MB Scene Creator** in der Seitenleiste öffnen.

[Im Marketplace öffnen](https://my.home-assistant.io/redirect/hacs_repository/?owner=FlorianMette91&repository=MB-Scene-Creator&category=integration)

Der bestehende Linktyp `hacs_repository` öffnet auch den Marketplace.
Das Projekt ist nicht im allgemeinen Katalog eingetragen. Die Datei `hacs.json`
und die HACS-Prüfung bleiben Bestandteil des aktuellen Marketplace-Formats.

**Private Repositories:** Der Marketplace liest ausschließlich öffentliche
GitHub-Repositories. Bei einem privaten Projekt erfolgt die Installation manuell:
`custom_components/mb_scene_creator` nach `/config/custom_components/` kopieren,
Home Assistant neu starten und die Integration hinzufügen. Updates ebenso übertragen;
das vorhandene Verzeichnis `userdata` mit eigenen Vorlagen dabei erhalten.

Quellen: [Marketplace](https://www.home-assistant.io/integrations/marketplace/),
[Repository-Anforderungen](https://contributors.home-assistant.io/marketplace/reference/repository-structure/).

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

## Scene Studio ersetzen

MB Scene Creator soll Scene Studio im persönlichen Betrieb ersetzen. Die eigene
Kennung (`mb_scene_creator`) sorgt für unabhängige Updates und Daten. Ein dauerhafter
Parallelbetrieb ist nicht erforderlich.

Vor dem Wechsel ein vollständiges Home-Assistant-Backup erstellen. Bestehende
Scene-Studio-Szenen und eigene Vorlagen werden in Version 0.1.0 **nicht automatisch
übernommen**. Scene Studio deshalb noch nicht löschen, wenn diese Daten weiter
benötigt werden. Die Datenübernahme muss vor dem endgültigen Wechsel vorbereitet werden.

Für einen Test kann Scene Studio deaktiviert und MB Scene Creator allein verwendet
werden. Bestehende Automationen und Dashboard-Verweise auf alte Szenen oder Dienste
müssen beim Wechsel berücksichtigt werden. Die neue Raumkarte heißt
`custom:mb-scene-creator-room-card`. Der vorhandene Importdialog betrifft das ältere
**Scene Presets**, nicht Scene Studio.

## Updates und Entwicklung

Bei öffentlichem Repository werden neue veröffentlichte Versionen über den Marketplace
angeboten. Bei privatem Repository erfolgt die Aktualisierung außerhalb des Marketplace.
Vor Updates ein Home-Assistant-Backup erstellen. Eigene Vorlagen liegen im persistenten
Verzeichnis `userdata` der Integration.

Entwicklungsablauf und Prüfungen: [DEVELOPMENT.md](DEVELOPMENT.md).
Fehler oder Wünsche: [Issues](https://github.com/FlorianMette91/MB-Scene-Creator/issues).

Die erste Version wurde automatisiert geprüft; Tests mit realen Lampen und deiner
Home-Assistant-Installation stehen noch aus.
