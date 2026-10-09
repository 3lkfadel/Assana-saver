# Utiliser Claude avec Infinity Planning

Ce guide s'adresse aux utilisateurs d'Infinity Planning qui veulent travailler sur leurs projets depuis Claude Desktop (ou Claude Code). Une fois le connecteur installé, vous pouvez demander à Claude, en langage courant, de faire le point sur un projet, de lister vos tâches de la semaine ou de créer les tâches d'un compte rendu de réunion.

Claude agit **en votre nom et avec vos droits** : il voit les projets que vous voyez, et ne peut modifier que ce que vous pouvez modifier vous-même. Chaque modification qu'il fait apparaît dans l'historique de la tâche avec la mention « via Claude ».

## Ce qu'il vous faut

- **Claude Desktop**, installé sur votre ordinateur (macOS ou Windows) et connecté à votre compte Claude. Il se télécharge sur [claude.ai/download](https://claude.ai/download).
- **Node.js**, qui sert de passerelle entre Claude Desktop et Infinity Planning. Installez la version « LTS » depuis [nodejs.org](https://nodejs.org), avec les options par défaut. Il n'y a rien d'autre à faire avec.
- Votre **compte Infinity Planning**.

Comptez dix minutes pour l'installation, à faire une seule fois.

## Étape 1 : générer votre jeton Claude

Le jeton est la clé qui permet à Claude d'accéder à Infinity Planning à votre place.

1. Dans Infinity Planning, ouvrez les **paramètres de votre profil**, puis, dans la rubrique **Développeur**, la page **Connecter Claude**.
2. Choisissez la **durée de validité** : 30 jours, 90 jours (recommandé), 1 an ou sans expiration.
3. Cliquez sur **Générer un jeton**.
4. Le jeton s'affiche **une seule fois**. Ne fermez pas la page avant d'avoir terminé l'étape 2 : les commandes affichées plus bas contiennent déjà votre jeton.

Votre jeton vaut un mot de passe : ne le partagez pas, ne l'envoyez pas par e-mail ou messagerie. Si vous pensez qu'il a été vu par quelqu'un d'autre, révoquez-le (voir plus bas) et générez-en un nouveau.

## Étape 2 : ajouter Infinity Planning à Claude Desktop

1. Sur la page **Connecter Claude**, dans la partie **Claude Desktop**, copiez le bloc de configuration avec le bouton de copie.
2. Ouvrez Claude Desktop, puis ses **paramètres** : menu **Claude > Settings** sur macOS, menu **≡ > File > Settings** sur Windows.
3. Ouvrez la rubrique **Developer** (Développeur), puis cliquez sur **Edit Config** (Modifier la configuration). Le fichier `claude_desktop_config.json` s'ouvre dans un éditeur de texte, ou son dossier s'affiche : ouvrez alors le fichier avec un éditeur de texte (TextEdit sur macOS, Bloc-notes sur Windows).
4. Collez le bloc copié :
   - **si le fichier est vide** ou ne contient que `{}`, remplacez tout son contenu par le bloc ;
   - **s'il contient déjà quelque chose**, ne remplacez rien : demandez de l'aide à votre référent informatique, ou demandez à Claude lui-même de fusionner les deux en lui collant le contenu actuel du fichier et le bloc. Le bloc `infinity-planning` doit se retrouver à l'intérieur de `"mcpServers"`.
5. Enregistrez le fichier.
6. **Quittez complètement Claude Desktop**, puis rouvrez-le. Fermer la fenêtre ne suffit pas :
   - sur macOS, menu **Claude > Quit** ou ⌘Q ;
   - sur Windows, clic droit sur l'icône Claude dans la barre des tâches (près de l'horloge), puis **Quit**.

Pour vérifier : dans une nouvelle conversation, ouvrez le menu des outils (l'icône près de la zone de saisie). **infinity-planning** doit y figurer. Demandez ensuite à Claude : « Qui suis-je dans Infinity Planning ? ». Il doit répondre avec votre nom et la date du jour.

### Avec Claude Code (développeurs)

Sur la page **Connecter Claude**, copiez la commande de la partie **Claude Code** et exécutez-la dans un terminal. Elle a la forme :

```bash
claude mcp add --transport http infinity-planning https://<adresse d'Infinity Planning>/mcp --header "Authorization: Bearer <votre jeton>"
```

Node.js n'est pas nécessaire dans ce cas.

## Les autorisations

La première fois que Claude veut utiliser un outil d'Infinity Planning, Claude Desktop vous demande votre accord. Pour ne pas être sollicité à chaque fois :

- choisissez **« Toujours autoriser »** (Allow always) pour les outils de consultation et de création ;
- gardez la confirmation pour les outils qui suppriment : `delete_task`, `delete_comment`, `remove_project_member` et `update_custom_field` (qui peut supprimer des options d'un champ).

Vous pouvez changer ces choix à tout moment dans les paramètres de Claude Desktop, rubrique **Connectors** (Connecteurs).

## Que demander à Claude ?

Parlez-lui comme à un collègue. Nommez le projet (par son nom ou son code, par exemple IAT) et désignez les tâches par leur identifiant (IAT-12) quand vous le connaissez.

**Faire le point**

- « Qu'est-ce que j'ai à faire cette semaine ? Commence par ce qui est en retard. »
- « Fais-moi le point sur le projet IAT : tâches en retard, échéances de la semaine, charge par personne. »
- « Quelles tâches de Kofi sont en retard, tous projets confondus ? »
- « Montre-moi la tâche IAT-12 avec ses commentaires et son historique. »

**Créer**

- « Voici le compte rendu de la réunion de ce matin : crée une tâche par action dans le projet IAT, avec le responsable et l'échéance quand ils sont cités. »
- « Découpe le développement du projet PROSUMA en tâches dans la section Backlog, assignées à moi. »
- « Ajoute une sous-tâche "Chiffrer les licences" à IAT-12, pour vendredi. »

**Mettre à jour**

- « Marque IAT-12 et IAT-15 comme terminées. »
- « Mets le champ Budget à 1 500 000 sur toutes les tâches du lot 2. »
- « Décale de deux semaines toutes les échéances des tâches ouvertes de la section Recette. »
- « Ajoute un commentaire sur IAT-12 : validé par le client ce matin. »

**Organiser** (selon vos droits sur le projet)

- « Crée une section "En recette" dans le projet IAT. »
- « Crée un champ personnalisé "Risque" de type liste, avec les options Faible, Moyen et Élevé, et ajoute-le au projet IAT. »
- « Ajoute Awa au projet IAT comme membre. »

Quelques conseils :

- **Avant une modification importante** (beaucoup de tâches, une suppression), Claude doit vous montrer ce qu'il va faire et attendre votre accord. Relisez avant de valider.
- **Claude donne des liens** vers les tâches : ouvrez-les pour vérifier dans Infinity Planning.
- Si Claude ne trouve pas un nom (une section, une personne, une option), il reçoit la liste des noms existants et vous la propose. Rien n'est modifié dans ce cas.

## Ce que Claude ne peut pas faire

- Supprimer un projet ou un champ personnalisé.
- Inviter quelqu'un dans l'organisation ou changer son rôle dans l'organisation.
- Ajouter à un projet une personne qui n'en fait pas encore partie, sauf si vous êtes administrateur de l'organisation.
- Accéder à un projet dont vous n'êtes pas membre.

## Gérer votre jeton

La page **Connecter Claude** liste vos jetons Claude, avec leur date d'expiration. Un avertissement apparaît 14 jours avant l'échéance.

- **Le jeton arrive à expiration** : générez-en un nouveau, puis remplacez l'ancien dans `claude_desktop_config.json` (la partie après `Bearer `). Quittez et rouvrez Claude Desktop.
- **Vous changez d'ordinateur ou pensez que le jeton a fuité** : cliquez sur **Révoquer**. Le jeton cesse de fonctionner immédiatement.

## En cas de problème

| Ce que vous voyez                                        | Que faire                                                                                                                                                                                                                                      |
| -------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **infinity-planning** n'apparaît pas dans Claude Desktop | Vérifiez que vous avez bien quitté puis rouvert Claude Desktop. Vérifiez que Node.js est installé. Si le problème persiste, le fichier de configuration est peut-être mal formé : une virgule ou une accolade manque souvent après un collage. |
| Claude dit que le jeton est invalide ou expiré           | Générez un nouveau jeton et remplacez l'ancien dans la configuration.                                                                                                                                                                          |
| Claude dit que vous n'avez pas accès                     | Vous n'êtes pas membre du projet, ou l'action demande des droits d'administrateur du projet.                                                                                                                                                   |
| Claude dit que la limite d'utilisation est atteinte      | Attendez une minute et redemandez.                                                                                                                                                                                                             |
| Claude dit qu'Infinity Planning est injoignable          | Vérifiez que vous accédez à Infinity Planning dans votre navigateur.                                                                                                                                                                           |

Si vous contactez votre référent informatique, joignez le journal du connecteur :

- sur macOS : `~/Library/Logs/Claude/mcp-server-infinity-planning.log` ;
- sur Windows : `%APPDATA%\Claude\logs\mcp-server-infinity-planning.log`.

Ne joignez jamais votre fichier `claude_desktop_config.json` : il contient votre jeton.
