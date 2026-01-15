
# ADD TO GmailHelperTool class in tools/gmail_helper_tool.py

def filter_response_by_intent(self, gmail_data: dict, user_intent: str) -> dict:
    """Filter Gmail response based on user intent"""
    
    if user_intent == 'sender_request':
        return {
            'from': gmail_data.get('from'),
            'intent': user_intent,
            'focused_field': 'sender'
        }
    elif user_intent == 'subject_request':
        return {
            'subject': gmail_data.get('subject'),
            'intent': user_intent,
            'focused_field': 'subject'
        }
    elif user_intent == 'attachment_request':
        return {
            'has_attachments': gmail_data.get('has_attachments'),
            'attachments': gmail_data.get('attachments', []),
            'intent': user_intent,
            'focused_field': 'attachments'
        }
    elif user_intent == 'date_request':
        return {
            'date': gmail_data.get('date'),
            'intent': user_intent,
            'focused_field': 'date'
        }
    else:
        return gmail_data

# MODIFY _get_latest_email_subject method to accept and use user_intent
def _get_latest_email_subject(self, user_id: str = None, max_results: int = 1, user_intent: str = None) -> MCPToolResult:
    """Son gelen email'in subject bilgisini al with intent awareness"""
    try:
        # ... existing code for getting email details ...
        
        if details_result.success:
            # Get full email data
            full_data = {
                'subject': details_result.data.get('subject'),
                'from': details_result.data.get('from'),
                'date': details_result.data.get('date'),
                'message_id': message_id,
                'thread_id': messages[0].get('threadId'),
                'has_attachments': len(details_result.data.get('attachments', [])) > 0,
                'attachments': details_result.data.get('attachments', [])
            }
            
            # Filter response based on user intent
            if user_intent:
                filtered_data = self.filter_response_by_intent(full_data, user_intent)
                logger.info(f"INTENT FILTERING: {user_intent} -> {list(filtered_data.keys())}")
                return MCPToolResult(success=True, data=filtered_data)
            else:
                return MCPToolResult(success=True, data=full_data)
        
        # ... rest of existing method ...
