# from drf_spectacular.utils import extend_schema, extend_schema_view


# @extend_schema_view(
#     create=extend_schema(
#         summary="Register a new user",
#         description="Creates a new user account with the provided credentials.",
#     ),
#     modify=extend_schema(
#         summary="Update user details",
#         description="Updates the profile details of the currently authenticated user.",
#     ),
#     me_get=extend_schema(
#         methods=["GET"],
#         summary="Retrieve current user profile",
#     ),
#     # # 2. Target the PUT method on the 'me' action
#     # me_put=extend_schema(
#     #     methods=["PUT"],
#     #     summary="Replace current user profile",
#     #     description="Overwrites entire profile structure for the authenticated user session.",
#     # ),
#     # 3. Target the PATCH method on the 'me' action
#     me_patch=extend_schema(
#         methods=["PATCH"],
#         summary="Modify current user profile",
#         description="Updates specific fields for the authenticated user session.",
#     ),
#     # 4. Target the DELETE method on the 'me' action
#     me_delete=extend_schema(
#         methods=["DELETE"],
#         summary="Delete current user account",
#         description="Permanently deletes the profile associated with the authenticated user session.",
#     ),
# )
# class CustomUserViewSet(views.UserViewSet):
#     pass
#     # def me(self, request, *args, **kwargs):
#     #     return super().me(request, *args, **kwargs)


# # class CustomUserMeView(views.View):
# #     """
# #     Secured route: Fetches the current authenticated user instance
# #     via incoming 'Authorization: Bearer <token>' headers.
# #     """

# #     def get(self, request):
# #         serializer = UserSerializer(request.user)
# #         return Response(serializer.data, status=status.HTTP_200_OK)
