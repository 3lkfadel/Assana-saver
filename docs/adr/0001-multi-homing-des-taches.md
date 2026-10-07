# Une tâche peut appartenir à plusieurs projets (multi-homing)

Plane rattache chaque tâche à un seul projet par une clé étrangère. Pour reproduire Asana, une tâche peut appartenir à zéro, un ou plusieurs projets : le lien tâche-projet devient une **appartenance** (une par projet, chacune avec sa section), et la tâche n'a plus de projet d'origine. Conséquences : l'identifiant d'une tâche est unique à l'espace de travail et ne dépend d'aucun projet (`T-1234`, et non `PROJ-123`) ; une tâche sans appartenance est possible (tâche personnelle dans « Mes tâches ») ; une sous-tâche n'appartient à aucun projet par défaut, elle n'est visible que depuis sa tâche parente sauf si on l'ajoute explicitement à un projet.

## Options écartées

- **Projet d'origine + liens vers d'autres projets** : plus simple, mais l'identifiant `PROJ-123` devient faux dès que la tâche quitte son projet d'origine, et l'expérience diverge d'Asana.
- **Pas de multi-homing** : les équipes du groupe l'utilisent dans Asana.

## Mise en œuvre progressive (2026-10-07)

L'inventaire de l'usage Asana (6 projets visibles, 195 tâches) n'a montré aucune tâche multi-homée. Le modèle d'appartenance est construit dès la phase 1, car les sections en ont besoin (ADR 0002), et il permet plusieurs projets par tâche. En revanche, l'interface pour ajouter une tâche à un autre projet attend le retour de l'équipe pilote. Ce n'est pas un retour au modèle « une tâche, un projet ».
