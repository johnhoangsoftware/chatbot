# ingest_service/adapters/jira_adapter.py
"""
Adapter for collecting data from Jira (issues, comments, attachments).
"""
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime

from .base import BaseAdapter, CollectedDocument
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class JiraAdapter(BaseAdapter):
    """
    Adapter for collecting documents from Jira.
    Fetches issues with comments and descriptions via Jira REST API.
    """
    
    def __init__(
        self, 
        jira_url: str,
        email: str,
        api_token: str,
        project_key: Optional[str] = None,
        jql: Optional[str] = None,
        max_results: int = 100
    ):
        """
        Initialize Jira adapter.
        
        Args:
            jira_url: Jira instance URL (e.g., https://your-domain.atlassian.net)
            email: User email for authentication (required)
            api_token: Jira API token (required)
            project_key: Optional project key to filter (e.g., 'PROJ')
            jql: Optional custom JQL query
            max_results: Maximum number of issues to fetch (default: 100)
        """
        if not jira_url:
            raise ValueError("jira_url is required")
        if not email:
            raise ValueError("email is required")
        if not api_token:
            raise ValueError("api_token is required")
            
        self.jira_url = jira_url.rstrip('/')
        self.email = email
        self.api_token = api_token
        self.project_key = project_key
        self.jql = jql
        self.max_results = max_results
        
        # Build default JQL if not provided
        if not self.jql and self.project_key:
            self.jql = f"project = {self.project_key} ORDER BY created DESC"
        elif not self.jql:
            self.jql = "ORDER BY created DESC"
    
    @property
    def source_type(self) -> str:
        return "jira"
    
    def validate(self, **kwargs) -> bool:
        """Validate Jira credentials and connection."""
        if not self.jira_url:
            logger.error("Jira URL is required")
            return False
        
        if not self.email or not self.api_token:
            logger.error("Jira email and API token are required")
            return False
        
        try:
            # Test connection with a simple API call
            response = requests.get(
                f"{self.jira_url}/rest/api/3/myself",
                auth=(self.email, self.api_token),
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to validate Jira connection: {e}")
            return False
    
    def _get_headers(self) -> dict:
        """Get headers for API requests."""
        return {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    
    def _fetch_issues(self) -> List[dict]:
        """Fetch issues from Jira using JQL."""
        all_issues = []
        start_at = 0
        max_results = 50  # Jira API pagination limit
        
        try:
            while True:
                url = f"{self.jira_url}/rest/api/3/search"
                params = {
                    'jql': self.jql,
                    'startAt': start_at,
                    'maxResults': max_results,
                    'fields': 'summary,description,comment,created,updated,status,priority,assignee,reporter,issuetype,labels'
                }
                
                response = requests.get(
                    url,
                    auth=(self.email, self.api_token),
                    headers=self._get_headers(),
                    params=params,
                    timeout=30
                )
                
                if response.status_code != 200:
                    logger.error(f"Failed to fetch issues: {response.status_code} - {response.text}")
                    break
                
                data = response.json()
                issues = data.get('issues', [])
                all_issues.extend(issues)
                
                logger.info(f"Fetched {len(issues)} issues (total: {len(all_issues)})")
                
                # Check if we've reached the limit or there are no more issues
                if len(all_issues) >= self.max_results or len(issues) < max_results:
                    break
                
                start_at += max_results
            
            return all_issues[:self.max_results]
            
        except Exception as e:
            logger.error(f"Error fetching Jira issues: {e}")
            return []
    
    def _format_issue_content(self, issue: dict) -> str:
        """Format issue data into readable text content."""
        fields = issue.get('fields', {})
        
        # Extract basic information
        issue_key = issue.get('key', 'N/A')
        summary = fields.get('summary', 'No summary')
        description = fields.get('description', '')
        
        # Parse description (handle Atlassian Document Format)
        description_text = self._parse_adf(description) if isinstance(description, dict) else description
        
        # Extract metadata
        status = fields.get('status', {}).get('name', 'Unknown')
        priority = fields.get('priority', {}).get('name', 'Unknown')
        issue_type = fields.get('issuetype', {}).get('name', 'Unknown')
        created = fields.get('created', 'Unknown')
        updated = fields.get('updated', 'Unknown')
        
        # Extract assignee and reporter
        assignee = fields.get('assignee', {})
        assignee_name = assignee.get('displayName', 'Unassigned') if assignee else 'Unassigned'
        
        reporter = fields.get('reporter', {})
        reporter_name = reporter.get('displayName', 'Unknown') if reporter else 'Unknown'
        
        # Extract labels
        labels = fields.get('labels', [])
        labels_text = ', '.join(labels) if labels else 'None'
        
        # Build content
        content_parts = [
            f"Issue: {issue_key}",
            f"Type: {issue_type}",
            f"Status: {status}",
            f"Priority: {priority}",
            f"",
            f"Summary: {summary}",
            f"",
            f"Description:",
            description_text or "No description provided",
            f"",
            f"Reporter: {reporter_name}",
            f"Assignee: {assignee_name}",
            f"Labels: {labels_text}",
            f"Created: {created}",
            f"Updated: {updated}",
        ]
        
        # Add comments
        comments = fields.get('comment', {}).get('comments', [])
        if comments:
            content_parts.append("")
            content_parts.append("=" * 50)
            content_parts.append("COMMENTS:")
            content_parts.append("=" * 50)
            
            for idx, comment in enumerate(comments, 1):
                author = comment.get('author', {}).get('displayName', 'Unknown')
                created = comment.get('created', 'Unknown')
                body = comment.get('body', '')
                
                # Parse comment body (handle ADF)
                comment_text = self._parse_adf(body) if isinstance(body, dict) else body
                
                content_parts.append(f"\nComment #{idx} by {author} on {created}:")
                content_parts.append(comment_text or "No content")
        
        return "\n".join(content_parts)
    
    def _parse_adf(self, adf_content: dict) -> str:
        """
        Parse Atlassian Document Format (ADF) to plain text.
        Simplified parser for common content types.
        """
        if not adf_content or not isinstance(adf_content, dict):
            return ""
        
        def extract_text(node: dict) -> str:
            """Recursively extract text from ADF nodes."""
            if not isinstance(node, dict):
                return ""
            
            node_type = node.get('type', '')
            text_parts = []
            
            # Handle text nodes
            if node_type == 'text':
                return node.get('text', '')
            
            # Handle content array
            content = node.get('content', [])
            if isinstance(content, list):
                for child in content:
                    child_text = extract_text(child)
                    if child_text:
                        text_parts.append(child_text)
            
            # Add spacing for paragraphs
            if node_type == 'paragraph' and text_parts:
                return '\n'.join(text_parts) + '\n'
            
            # Handle headings
            if node_type == 'heading':
                level = node.get('attrs', {}).get('level', 1)
                heading_text = ''.join(text_parts)
                return f"{'#' * level} {heading_text}\n"
            
            # Handle lists
            if node_type in ('bulletList', 'orderedList'):
                return '\n'.join(f"- {item}" for item in text_parts if item.strip())
            
            return ' '.join(text_parts)
        
        return extract_text(adf_content).strip()
    
    def collect(self, **kwargs) -> List[CollectedDocument]:
        """
        Collect issues from Jira.
        
        Returns:
            List of CollectedDocument objects
        """
        results = []
        
        try:
            logger.info(f"Fetching Jira issues from {self.jira_url}")
            logger.info(f"Using JQL: {self.jql}")
            
            # Fetch issues
            issues = self._fetch_issues()
            
            if not issues:
                logger.warning("No issues found")
                return results
            
            # Process each issue
            for issue in issues:
                try:
                    issue_key = issue.get('key', 'unknown')
                    fields = issue.get('fields', {})
                    
                    # Format content
                    content = self._format_issue_content(issue)
                    
                    if not content.strip():
                        logger.warning(f"Empty content for issue {issue_key}, skipping")
                        continue
                    
                    # Extract chunk config if provided
                    chunk_config = kwargs.get("chunk_config", {})
                    
                    # Create document
                    doc = CollectedDocument(
                        raw_id=self.generate_raw_id(),
                        content=content,
                        source_type=self.source_type,
                        source_path=f"{self.jira_url}/browse/{issue_key}",
                        source_name=f"{issue_key}: {fields.get('summary', 'No summary')}",
                        metadata={
                            "jira_url": self.jira_url,
                            "issue_key": issue_key,
                            "issue_type": fields.get('issuetype', {}).get('name', 'Unknown'),
                            "status": fields.get('status', {}).get('name', 'Unknown'),
                            "priority": fields.get('priority', {}).get('name', 'Unknown'),
                            "created": fields.get('created', 'Unknown'),
                            "updated": fields.get('updated', 'Unknown'),
                            "labels": fields.get('labels', []),
                            "comment_count": len(fields.get('comment', {}).get('comments', [])),
                            "content_size": len(content),
                            "chunk_config": chunk_config
                        }
                    )
                    
                    results.append(doc)
                    logger.info(f"Collected issue: {issue_key}")
                    
                except Exception as e:
                    logger.warning(f"Error processing issue: {e}")
                    continue
            
            logger.info(f"JiraAdapter collected {len(results)} issues from {self.jira_url}")
            
        except Exception as e:
            logger.error(f"Error collecting from Jira: {e}")
        
        return results
