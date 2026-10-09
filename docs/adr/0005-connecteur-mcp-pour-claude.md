# Un serveur MCP maison pour piloter Infinity Planning depuis Claude

Les développeurs (Claude Code) et les managers des filiales (Claude Desktop) doivent pouvoir lire et modifier Infinity Planning depuis Claude, chacun avec ses propres droits. Nous écrivons notre propre serveur MCP, `apps/mcp`, en Python avec FastMCP. Il expose une vingtaine d'outils orientés intention dans le vocabulaire d'Asana (`search_tasks`, `create_tasks`, `set_custom_field_values`…), annotés lecture ou destructif, et n'appelle que l'API publique `/api/v1/` : les permissions, validations et limites de débit existantes s'appliquent donc telles quelles. L'organisation est fixée côté serveur. Une fois déployé, il est servi sous `/mcp` sur le domaine de l'application.

Chaque utilisateur s'authentifie avec un jeton personnel envoyé en `Authorization: Bearer`. C'est un `APIToken` marqué MCP, valable 90 jours par défaut, révocable et créé depuis une page « Connecter Claude » qui donne la commande `claude mcp add` et la configuration de Claude Desktop (via `mcp-remote` ou une extension `.mcpb`). Les actions faites par ce jeton apparaissent « via Claude » dans l'activité des tâches.

L'API publique est complétée pour le serveur : champs personnalisés (définitions et valeurs), endpoints groupés de création et de mise à jour des tâches (100 tâches au plus par appel), et limite de débit de 300 requêtes par minute pour les jetons MCP. Les routes v1 des cycles, modules et estimations sont fermées, puisque ces fonctions sont écartées.

Périmètre des outils : lecture, écriture courante et administration des projets, sections, labels, définitions de champs et membres de projet. Sont exclus les invitations et rôles au niveau de l'organisation, la suppression de projets et de champs, ainsi que les cycles, modules, estimations et multi-assignés. Seules les tâches et les commentaires peuvent être supprimés.

## Options écartées

- **Le serveur MCP officiel de Plane, tel quel ou forké** : il expose les cycles, modules et fonctions payantes que nous avons retirés, ignore les champs personnalisés, et son OAuth repose sur un fournisseur que notre fork n'a pas.
- **Un serveur intégré au process Django, avec accès direct à l'ORM** : il contournerait les permissions de l'API publique.
- **Une clé partagée par toute l'organisation** (en-têtes fixes d'un connecteur claude.ai) : toutes les actions seraient faites au nom d'un seul compte, sans droits par personne ni traçabilité.
- **OAuth 2.1 dès maintenant** : c'est le seul moyen d'utiliser l'interface Connecteurs de claude.ai, mais il demande un serveur d'autorisation dans Django. Il est reporté ; le serveur MCP est écrit pour pouvoir l'accepter plus tard.
