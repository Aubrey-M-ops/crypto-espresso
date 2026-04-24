"""
Telegram authentication and session management using Telethon.

Provides authenticated TelegramClient with automatic login handling,
session persistence, and error recovery.
"""

import os
import logging
from pathlib import Path
from typing import Optional

from telethon import TelegramClient
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    FloodWaitError
)
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TelegramAuthError(Exception):
    """Base exception for Telegram authentication errors."""
    pass


class TelegramAuth:
    """
    Telegram authentication manager with session persistence.
    
    Handles phone-based authentication, 2FA if enabled, and session
    caching to avoid repeated logins.
    """
    
    # Default session storage directory (absolute path based on project root)
    SESSION_DIR = Path(__file__).parent.parent / "sessions"
    SESSION_FILE = "telegram.session"
    
    def __init__(
        self,
        api_id: Optional[int] = None,
        api_hash: Optional[str] = None,
        phone: Optional[str] = None,
        session_path: Optional[Path] = None,
        interactive: bool = False
    ):
        """
        Initialize Telegram authentication manager.
        
        Args:
            api_id: Telegram API ID (from my.telegram.org). If None, reads from TELEGRAM_API_ID env var.
            api_hash: Telegram API hash. If None, reads from TELEGRAM_API_HASH env var.
            phone: Phone number in international format (+1234567890). If None, reads from TELEGRAM_PHONE.
            session_path: Custom session file path. If None, uses ./sessions/telegram.session.
        
        Raises:
            ValueError: If required credentials are not provided or found in environment.
        """
        # Read credentials from environment if not provided
        self.api_id = api_id or os.getenv("TELEGRAM_API_ID")
        self.api_hash = api_hash or os.getenv("TELEGRAM_API_HASH")
        self.phone = phone or os.getenv("TELEGRAM_PHONE")
        
        # Validate credentials
        if not self.api_id:
            raise ValueError(
                "TELEGRAM_API_ID not found. "
                "Set it in .env or pass as argument. "
                "Get it from https://my.telegram.org"
            )
        if not self.api_hash:
            raise ValueError(
                "TELEGRAM_API_HASH not found. "
                "Set it in .env or pass as argument."
            )
        if not self.phone:
            raise ValueError(
                "TELEGRAM_PHONE not found. "
                "Set it in .env or pass as argument. "
                "Format: +1234567890 (international format with +)"
            )
        
        # Convert api_id to int if it's a string
        try:
            self.api_id = int(self.api_id)
        except (ValueError, TypeError) as e:
            raise ValueError(f"TELEGRAM_API_ID must be numeric, got: {self.api_id}") from e
        
        # Setup session path
        if session_path:
            self.session_path = Path(session_path)
        else:
            self.session_path = self.SESSION_DIR / self.SESSION_FILE
        
        # Ensure session directory exists
        self.session_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.interactive = interactive
        self._client: Optional[TelegramClient] = None

        logger.info(
            f"Initialized TelegramAuth for {self.phone} "
            f"(session: {self.session_path})"
        )
    
    async def get_client(self) -> TelegramClient:
        """
        Get authenticated TelegramClient, performing login if necessary.
        
        This method:
        1. Creates a TelegramClient instance
        2. Checks if session already exists (auto-login)
        3. If not, performs phone-based authentication with interactive code input
        4. Handles 2FA password if enabled
        5. Saves session for future use
        
        Returns:
            Authenticated and connected TelegramClient instance
        
        Raises:
            TelegramAuthError: If authentication fails after retries
        
        Example:
            >>> auth = TelegramAuth()
            >>> client = await auth.get_client()
            >>> # Use client for API calls
            >>> await client.send_message('me', 'Hello!')
        """
        # Return existing client if already authenticated
        if self._client and self._client.is_connected():
            logger.debug("Reusing existing authenticated client")
            return self._client
        
        # Create new client
        logger.info(f"Creating TelegramClient with session: {self.session_path}")
        client = TelegramClient(
            str(self.session_path),
            self.api_id,
            self.api_hash
        )
        
        try:
            # Connect to Telegram servers
            await client.connect()
            logger.info("Connected to Telegram servers")
            
            # Check if already authorized
            if await client.is_user_authorized():
                logger.info("✅ Already authorized (using existing session)")
                self._client = client
                return client

            # Not authorized - only attempt interactive login if explicitly enabled
            if not self.interactive:
                raise TelegramAuthError(
                    "No valid Telegram session found. "
                    "Run 'python src/setup_kol.py' interactively on the server to authenticate, "
                    "or copy a valid session file to the sessions/ directory."
                )

            logger.info(f"Not authorized. Starting phone authentication for {self.phone}")
            await self._perform_login(client)
            
            # Verify authorization succeeded
            if not await client.is_user_authorized():
                raise TelegramAuthError("Authorization failed: user not authorized after login")
            
            logger.info("✅ Successfully authenticated and saved session")
            self._client = client
            return client
            
        except FloodWaitError as e:
            logger.error(f"Flood wait error: must wait {e.seconds} seconds")
            raise TelegramAuthError(
                f"Telegram rate limit hit. Please wait {e.seconds} seconds and try again."
            ) from e
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            # Cleanup on failure
            if client.is_connected():
                await client.disconnect()
            raise TelegramAuthError(f"Failed to authenticate: {e}") from e
    
    async def _perform_login(self, client: TelegramClient) -> None:
        """
        Perform interactive phone-based login.
        
        Args:
            client: Connected but unauthorized TelegramClient
        
        Raises:
            TelegramAuthError: If login fails
        """
        max_code_attempts = 3
        
        # Send authentication code
        logger.info(f"Sending authentication code to {self.phone}...")
        try:
            await client.send_code_request(self.phone)
            logger.info("✅ Code sent! Check your Telegram app.")
        except Exception as e:
            raise TelegramAuthError(f"Failed to send code: {e}") from e
        
        # Prompt user for code
        for attempt in range(1, max_code_attempts + 1):
            try:
                code = input(
                    f"\n🔐 Enter the 5-digit code from Telegram (attempt {attempt}/{max_code_attempts}): "
                ).strip()
                
                if not code:
                    logger.warning("Empty code provided")
                    continue
                
                logger.info(f"Attempting sign in with code: {code}")
                await client.sign_in(self.phone, code)
                logger.info("✅ Code accepted!")
                return
                
            except PhoneCodeInvalidError:
                logger.warning(f"Invalid code (attempt {attempt}/{max_code_attempts})")
                if attempt >= max_code_attempts:
                    raise TelegramAuthError(
                        f"Invalid code after {max_code_attempts} attempts. Please try again later."
                    )
                print("❌ Invalid code. Please try again.")
                
            except PhoneCodeExpiredError:
                logger.error("Code expired")
                raise TelegramAuthError(
                    "Authentication code expired. Please restart the authentication process."
                )
                
            except SessionPasswordNeededError:
                # 2FA enabled - need password
                logger.info("Two-factor authentication (2FA) is enabled")
                await self._handle_2fa(client)
                return
                
            except Exception as e:
                logger.error(f"Unexpected error during code entry: {e}")
                raise TelegramAuthError(f"Login failed: {e}") from e
        
        raise TelegramAuthError("Failed to sign in after maximum code attempts")
    
    async def _handle_2fa(self, client: TelegramClient) -> None:
        """
        Handle two-factor authentication password prompt.
        
        Args:
            client: TelegramClient that requires 2FA password
        
        Raises:
            TelegramAuthError: If 2FA password is incorrect
        """
        max_password_attempts = 3
        
        for attempt in range(1, max_password_attempts + 1):
            try:
                password = input(
                    f"\n🔒 Enter your 2FA password (attempt {attempt}/{max_password_attempts}): "
                ).strip()
                
                if not password:
                    logger.warning("Empty password provided")
                    continue
                
                await client.sign_in(password=password)
                logger.info("✅ 2FA password accepted!")
                return
                
            except Exception as e:
                logger.warning(f"2FA password failed (attempt {attempt}/{max_password_attempts}): {e}")
                if attempt >= max_password_attempts:
                    raise TelegramAuthError(
                        f"Incorrect 2FA password after {max_password_attempts} attempts"
                    ) from e
                print("❌ Incorrect password. Please try again.")
        
        raise TelegramAuthError("Failed 2FA authentication")
    
    async def disconnect(self) -> None:
        """
        Disconnect the Telegram client.
        
        Call this when done using the client to cleanly close the connection.
        """
        if self._client and self._client.is_connected():
            logger.info("Disconnecting Telegram client")
            await self._client.disconnect()
            self._client = None
    
    async def logout(self) -> None:
        """
        Logout and delete the saved session.
        
        This will require re-authentication on next get_client() call.
        
        Raises:
            TelegramAuthError: If logout fails
        """
        try:
            if self._client:
                logger.info("Logging out from Telegram")
                await self._client.log_out()
                self._client = None
            
            # Delete session file
            if self.session_path.exists():
                logger.info(f"Deleting session file: {self.session_path}")
                self.session_path.unlink()
                
                # Also delete .session-journal if exists
                journal_path = Path(str(self.session_path) + "-journal")
                if journal_path.exists():
                    journal_path.unlink()
                    
            logger.info("✅ Logout complete")
            
        except Exception as e:
            logger.error(f"Logout failed: {e}")
            raise TelegramAuthError(f"Failed to logout: {e}") from e


# Convenience function for simple usage
async def get_client(
    api_id: Optional[int] = None,
    api_hash: Optional[str] = None,
    phone: Optional[str] = None
) -> TelegramClient:
    """
    Convenience function to get an authenticated Telegram client.
    
    Args:
        api_id: Telegram API ID (optional, reads from env)
        api_hash: Telegram API hash (optional, reads from env)
        phone: Phone number (optional, reads from env)
    
    Returns:
        Authenticated TelegramClient
    
    Raises:
        TelegramAuthError: If authentication fails
    
    Example:
        >>> client = await get_client()
        >>> me = await client.get_me()
        >>> print(f"Logged in as: {me.first_name}")
    """
    auth = TelegramAuth(api_id=api_id, api_hash=api_hash, phone=phone)
    return await auth.get_client()


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    async def test_auth():
        """Test authentication flow."""
        print("=" * 60)
        print("TELEGRAM AUTHENTICATION TEST")
        print("=" * 60)
        
        try:
            # Initialize auth manager
            auth = TelegramAuth(interactive=True)
            
            # Get authenticated client
            client = await auth.get_client()
            
            # Test: get own user info
            me = await client.get_me()
            print(f"\n✅ Successfully authenticated!")
            print(f"   Name: {me.first_name} {me.last_name or ''}")
            print(f"   Username: @{me.username}")
            print(f"   Phone: {me.phone}")
            print(f"   User ID: {me.id}")
            
            # Test: send a message to self
            print(f"\n📤 Sending test message to Saved Messages...")
            await client.send_message('me', '🤖 Test message from telegram_auth.py')
            print("✅ Message sent successfully!")
            
            # Cleanup
            await auth.disconnect()
            print("\n✅ Test complete!")
            
        except TelegramAuthError as e:
            print(f"\n❌ Authentication failed: {e}")
            return 1
            
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            logger.exception("Test failed with exception:")
            return 1
        
        return 0
    
    # Run test
    exit_code = asyncio.run(test_auth())
    exit(exit_code)
