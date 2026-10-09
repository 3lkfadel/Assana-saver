# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Group referential for the steering space (« espace de pilotage », cahier des charges §3 and §10).

The Group is organised in branches (« pôles »); each branch holds entities (subsidiaries,
departments); every project is carried by one entity. The Cabinet of the Presidency and the
CEO administer this referential and the steering profiles of the people who read it.
These tables live beside Plane's own models so that Plane's tables stay untouched (ADR 0003).
"""

# Django imports
from django.conf import settings
from django.db import models
from django.db.models import Q

# Module imports
from .base import BaseModel


class Branch(BaseModel):
    """A branch of the Group (« pôle »): Finance & Capital Markets, Immobilier, Fonctions Groupe…"""

    workspace = models.ForeignKey("db.Workspace", on_delete=models.CASCADE, related_name="steering_branches")
    name = models.CharField(max_length=255)
    sort_order = models.FloatField(default=65535)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "name"],
                condition=Q(deleted_at__isnull=True),
                name="steering_branch_unique_name_when_not_deleted",
            )
        ]
        db_table = "steering_branches"
        ordering = ("sort_order", "name")

    def __str__(self):
        return self.name


class Entity(BaseModel):
    """A company, subsidiary or department attached to exactly one branch."""

    workspace = models.ForeignKey("db.Workspace", on_delete=models.CASCADE, related_name="steering_entities")
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="entities")
    name = models.CharField(max_length=255)
    sort_order = models.FloatField(default=65535)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "name"],
                condition=Q(deleted_at__isnull=True),
                name="steering_entity_unique_name_when_not_deleted",
            )
        ]
        db_table = "steering_entities"
        ordering = ("sort_order", "name")

    def __str__(self):
        return self.name


class SteeringCategory(BaseModel):
    """Work item category kept by the Cabinet (Agréments, Gouvernance, Partenariats, Développement…)."""

    workspace = models.ForeignKey("db.Workspace", on_delete=models.CASCADE, related_name="steering_categories")
    name = models.CharField(max_length=255)
    sort_order = models.FloatField(default=65535)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "name"],
                condition=Q(deleted_at__isnull=True),
                name="steering_category_unique_name_when_not_deleted",
            )
        ]
        db_table = "steering_categories"
        ordering = ("sort_order", "name")

    def __str__(self):
        return self.name


class ProjectSteering(BaseModel):
    """Steering data of a project: the entity that carries it."""

    project = models.OneToOneField("db.Project", on_delete=models.CASCADE, related_name="steering")
    workspace = models.ForeignKey("db.Workspace", on_delete=models.CASCADE, related_name="project_steerings")
    entity = models.ForeignKey(Entity, on_delete=models.PROTECT, related_name="projects")

    class Meta:
        db_table = "project_steerings"


class SteeringProfileRole(models.TextChoices):
    CEO = "ceo", "PDG"
    CABINET = "cabinet", "Cabinet de la Présidence"
    BRANCH_DIRECTOR = "branch_director", "Directeur de pôle"
    ENTITY_MANAGER = "entity_manager", "Responsable d'entité"


class SteeringProfile(BaseModel):
    """
    What a person may see in the steering space: the whole Group (CEO, Cabinet), one branch
    (branch director) or one entity (entity manager). A person may hold several profiles.
    """

    workspace = models.ForeignKey("db.Workspace", on_delete=models.CASCADE, related_name="steering_profiles")
    member = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="steering_profiles")
    role = models.CharField(max_length=30, choices=SteeringProfileRole.choices)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, null=True, blank=True, related_name="profiles")
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, null=True, blank=True, related_name="profiles")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "member", "role", "branch", "entity"],
                condition=Q(deleted_at__isnull=True),
                name="steering_profile_unique_when_not_deleted",
                nulls_distinct=False,
            )
        ]
        db_table = "steering_profiles"
