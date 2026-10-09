# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python import
from datetime import timedelta
from uuid import uuid4
from typing import Optional

# Django imports
from django.utils import timezone

# Third party
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import status

# Module import
from .base import BaseAPIView
from plane.db.models import APIToken, APITokenClient
from plane.app.serializers import APITokenSerializer, APITokenReadSerializer


# Validity offered for client tokens (Claude), in days; None never expires
CLIENT_TOKEN_VALIDITY_DAYS = (30, 90, 365, None)
DEFAULT_CLIENT_TOKEN_VALIDITY_DAYS = 90


class ApiTokenEndpoint(BaseAPIView):
    def post(self, request: Request) -> Response:
        client = request.data.get("client", "")
        if client:
            return self._create_client_token(request, client)

        label = request.data.get("label", str(uuid4().hex))
        description = request.data.get("description", "")
        expired_at = request.data.get("expired_at", None)

        # Check the user type
        user_type = 1 if request.user.is_bot else 0

        api_token = APIToken.objects.create(
            label=label,
            description=description,
            user=request.user,
            user_type=user_type,
            expired_at=expired_at,
        )

        serializer = APITokenSerializer(api_token)
        # Token will be only visible while creating
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def _create_client_token(self, request: Request, client: str) -> Response:
        """A token for a client such as Claude: its validity is chosen in days and its changes are marked "via" it."""
        if client not in APITokenClient.values:
            return Response({"error": "Unknown client."}, status=status.HTTP_400_BAD_REQUEST)
        days = request.data.get("expires_in_days", DEFAULT_CLIENT_TOKEN_VALIDITY_DAYS)
        if isinstance(days, bool) or days not in CLIENT_TOKEN_VALIDITY_DAYS:
            return Response(
                {"error": "expires_in_days must be 30, 90, 365 or null."}, status=status.HTTP_400_BAD_REQUEST
            )
        api_token = APIToken.objects.create(
            label=str(request.data.get("label") or APITokenClient(client).label)[:255],
            description=str(request.data.get("description") or ""),
            user=request.user,
            user_type=1 if request.user.is_bot else 0,
            client=client,
            expired_at=timezone.now() + timedelta(days=days) if days else None,
        )
        # Token will be only visible while creating
        return Response(APITokenSerializer(api_token).data, status=status.HTTP_201_CREATED)

    def get(self, request: Request, pk: Optional[str] = None) -> Response:
        if pk is None:
            api_tokens = APIToken.objects.filter(user=request.user, is_service=False)
            serializer = APITokenReadSerializer(api_tokens, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            api_tokens = APIToken.objects.get(user=request.user, pk=pk, is_service=False)
            serializer = APITokenReadSerializer(api_tokens)
            return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request: Request, pk: str) -> Response:
        api_token = APIToken.objects.get(user=request.user, pk=pk, is_service=False)
        api_token.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def patch(self, request: Request, pk: str) -> Response:
        api_token = APIToken.objects.get(user=request.user, pk=pk, is_service=False)
        serializer = APITokenSerializer(api_token, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
