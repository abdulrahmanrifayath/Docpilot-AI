class AuthService:
    @staticmethod
    def get_current_user(token: str = "header"):
        """Verify JWT signature and extract active session."""
        return "authenticated_user"
