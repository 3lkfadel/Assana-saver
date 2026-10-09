# Chaque tâche porte une fiche de pilotage, dont un statut natif à six valeurs

Le cahier des charges (§4, §5) fait reposer tous les calculs de l'espace de pilotage sur des informations que chaque tâche doit porter. On y trouve un **statut** à six valeurs fixes : À démarrer, En cours, En validation, En attente, Terminé, Annulé. S'y ajoutent l'entité, la catégorie, le superviseur, l'approbateur, l'avancement, la cause d'attente, le risque, la clôture et le point de situation.

Ces informations vivent dans une table `issue_steerings`, une ligne par tâche, à côté de celles de Plane (ADR 0003). Les champs que Plane possède déjà restent sur la tâche : projet, responsable, priorité et deadline. Une tâche sans fiche se lit « À démarrer », à 0 %, portée par l'entité de son projet.

Le statut est indépendant des sections : déplacer une carte ne le change pas, et le changer ne déplace pas la carte. Cela précise l'ADR 0002, qui prévoyait un champ personnalisé « Statut ».

L'API applique les règles du §4 :

- le passage à En attente exige la cause ;
- le passage à Terminé exige une date de clôture, qui ne peut pas être future, et un commentaire, et impose 100 % ;
- le risque n'est plus modifiable une fois la tâche terminée ou annulée.

Chaque modification est inscrite dans l'historique de la tâche.

## Options écartées

- **Un champ personnalisé « Statut »** : ses valeurs seraient renommables projet par projet, alors que les règles de calcul (RG-01 à RG-14) dépendent de ces six valeurs exactes.
- **Le statut porté par les sections** : contraire à l'ADR 0002, où les sections sont un rangement libre propre à chaque projet.
