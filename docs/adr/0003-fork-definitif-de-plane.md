# Fork définitif de Plane

Asana-saver diverge définitivement de `makeplane/plane` : on ne fusionne plus `upstream/preview`. Le multi-homing (ADR 0001), les sections (ADR 0002) et le responsable unique modifient en profondeur les modèles `Issue`, `State` et les assignations, si bien que chaque fusion amont produirait des conflits plus coûteux que ce qu'elle apporte. On surveille les avis de sécurité de Plane et on reporte à la main les correctifs qui concernent du code encore partagé.
