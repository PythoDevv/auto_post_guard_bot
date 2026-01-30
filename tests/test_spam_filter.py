import unittest
from unittest.mock import MagicMock, AsyncMock, patch
from aiogram.types import Message, Chat
from utils.spam_filter_test_helper import check_spam

# Since we can't easily import the middleware class due to DB dependency setup in a simple script without creating a real memory DB,
# we will extract the logic to a helper or just mock heavily.
# Better approach: Create a simple script that imports the middleware and mocks the session.

from middlewares.spam_filter import SpamFilterMiddleware
from database.models import Group, Keyword, User

class TestSpamFilter(unittest.IsolatedAsyncioTestCase):
    async def test_spam_detection(self):
        # Setup Middleware
        middleware = SpamFilterMiddleware()
        
        # Mock Handler
        handler = AsyncMock(return_value="Passed")
        
        # Mock Event (Message)
        event = MagicMock(spec=Message)
        event.text = "Hello badword"
        event.caption = None
        event.chat = MagicMock(spec=Chat)
        event.chat.type = "supergroup"
        event.chat.id = -100123456789
        event.message_id = 123
        event.bot = AsyncMock()
        event.delete = AsyncMock()
        
        # Mock Data (Session)
        session = AsyncMock()
        data = {"session": session}
        
        # Mock DB results
        # 1. Get Group
        mock_group = Group(id=1, telegram_id=-100123456789, title="Test Group", owner_id=1)
        # 2. Get Keywords
        mock_keywords = ["badword", "spam"]
        # 3. Get Owner
        mock_owner = User(id=1, telegram_id=987654321, full_name="Owner", is_admin=0)
        
        # Configure session.execute to return these
        # We need to handle multiple calls to session.execute
        # First call: Select Group
        # Second call: Select Keywords
        # Third call: Select Owner
        
        # Create mock results
        mock_res_group = MagicMock()
        mock_res_group.scalars().first.return_value = mock_group
        
        mock_res_kw = MagicMock()
        mock_res_kw.scalars().all.return_value = mock_keywords
        
        mock_res_owner = MagicMock()
        mock_res_owner.scalars().first.return_value = mock_owner
        
        # Side effect for session.execute
        # We can just return different mocks based on query or call count.
        # Simpler: use side_effect with an iterator
        session.execute.side_effect = [mock_res_group, mock_res_kw, mock_res_owner]
        
        # Run Middleware
        result = await middleware(handler, event, data)
        
        # Assertions
        # Should not call handler (blocked)
        handler.assert_not_called()
        
        # Should delete message
        event.delete.assert_called_once()
        
        # Should forward to owner
        event.bot.forward_message.assert_called_once_with(
            chat_id=987654321,
            from_chat_id=-100123456789,
            message_id=123
        )
        
        print("Test Spam Detection: PASSED")

    async def test_no_spam(self):
         # Setup Middleware
        middleware = SpamFilterMiddleware()
        handler = AsyncMock(return_value="Passed")
        
        event = MagicMock(spec=Message)
        event.text = "Hello good world"
        event.caption = None
        event.chat = MagicMock(spec=Chat)
        event.chat.type = "supergroup"
        event.chat.id = -100123456789
        
        session = AsyncMock()
        data = {"session": session}
        
        mock_group = Group(id=1, telegram_id=-100123456789, title="Test Group", owner_id=1)
        mock_keywords = ["badword", "spam"]
        
        mock_res_group = MagicMock()
        mock_res_group.scalars().first.return_value = mock_group
        
        mock_res_kw = MagicMock()
        mock_res_kw.scalars().all.return_value = mock_keywords
        
        session.execute.side_effect = [mock_res_group, mock_res_kw]
        
        result = await middleware(handler, event, data)
        
        # Should call handler
        handler.assert_called_once()
        
        # Should NOT delete
        event.delete.assert_not_called()
        
        print("Test No Spam: PASSED")

if __name__ == "__main__":
    unittest.main()
