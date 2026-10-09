# Le référentiel du Groupe est natif : pôles, entités et profils de pilotage

L'espace de pilotage demandé par le cahier des charges (§3, §10) classe tout le travail par **pôle** puis par **entité** (filiale ou fonction support), et ce que chacun voit dépend de son **profil** : le PDG et le Cabinet de la Présidence voient tout le Groupe, un directeur de pôle voit son pôle, un responsable d'entité voit son entité. Nous ajoutons pour cela des tables propres (`steering_branches`, `steering_entities`, `steering_categories`, `project_steerings`, `steering_profiles`) à côté de celles de Plane, sans modifier ces dernières (ADR 0003). Chaque projet est porté par une seule entité ; le Cabinet, le PDG et les administrateurs de l'organisation administrent le référentiel ; tous les membres peuvent le lire pour choisir une entité ou une catégorie.

## Options écartées

- **Une équipe par entité** : les équipes servent à posséder des projets et à en régler l'accès ; une entité est une donnée de rattachement et de reporting. Les confondre forcerait à créer une équipe pour chaque fonction support et mélangerait droits d'accès et périmètre de lecture du pilotage.
- **Un champ personnalisé « Entité »** : ses valeurs seraient modifiables par n'importe quel projet, sans lien avec un pôle ni avec les profils, alors que les règles de filtrage et de reporting reposent sur cette hiérarchie.
