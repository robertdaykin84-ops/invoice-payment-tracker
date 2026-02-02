"""
Authentication Service for Client Onboarding

Provides user authentication with password hashing for production mode,
with demo mode fallback.
"""

import os
import hashlib
import secrets
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# Demo mode flag
DEMO_MODE = os.environ.get('AUTH_DEMO_MODE', 'true').lower() == 'true'

# Demo users (no passwords needed)
DEMO_USERS = {
    'bd_user': {'name': 'Sarah Johnson', 'role': 'bd', 'email': 'sarah.johnson@example.com'},
    'compliance_user': {'name': 'James Smith', 'role': 'compliance', 'email': 'james.smith@example.com'},
    'mlro_user': {'name': 'Emma Williams', 'role': 'mlro', 'email': 'emma.williams@example.com'},
    'admin_user': {'name': 'Michael Brown', 'role': 'admin', 'email': 'michael.brown@example.com'}
}

# Production users store (in-memory for demo, would be database in production)
_users_store: Dict[str, Dict] = {}


def _hash_password(password: str, salt: str = None) -> tuple:
    """Hash a password with salt."""
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return hashed.hex(), salt


def _verify_password(password: str, hashed: str, salt: str) -> bool:
    """Verify a password against its hash."""
    new_hash, _ = _hash_password(password, salt)
    return secrets.compare_digest(new_hash, hashed)


def create_user(
    user_id: str,
    name: str,
    email: str,
    role: str,
    password: str = None
) -> Dict[str, Any]:
    """
    Create a new user.

    Args:
        user_id: Unique user identifier
        name: Display name
        email: Email address
        role: User role (bd, compliance, mlro, admin)
        password: Password (required in production mode)

    Returns:
        Dict with status and user info
    """
    if user_id in _users_store or user_id in DEMO_USERS:
        return {'status': 'error', 'message': 'User already exists'}

    if not DEMO_MODE and not password:
        return {'status': 'error', 'message': 'Password required in production mode'}

    user_data = {
        'user_id': user_id,
        'name': name,
        'email': email,
        'role': role,
        'created_at': datetime.now().isoformat(),
        'active': True
    }

    if password:
        hashed, salt = _hash_password(password)
        user_data['password_hash'] = hashed
        user_data['password_salt'] = salt

    _users_store[user_id] = user_data
    logger.info(f"User created: {user_id}")

    # Return without sensitive data
    return {
        'status': 'success',
        'message': 'User created',
        'user': {k: v for k, v in user_data.items() if 'password' not in k}
    }


def authenticate_user(user_id: str, password: str = None) -> Optional[Dict]:
    """
    Authenticate a user.

    Args:
        user_id: User identifier
        password: Password (required in production mode)

    Returns:
        User dict if authenticated, None otherwise
    """
    # Check demo users first
    if DEMO_MODE and user_id in DEMO_USERS:
        return {**DEMO_USERS[user_id], 'id': user_id}

    # Check production users
    if user_id in _users_store:
        user = _users_store[user_id]
        if not user.get('active'):
            return None

        # In production mode, verify password
        if not DEMO_MODE:
            if not password:
                return None
            if not _verify_password(
                password,
                user.get('password_hash', ''),
                user.get('password_salt', '')
            ):
                return None

        return {
            'id': user_id,
            'name': user['name'],
            'email': user['email'],
            'role': user['role']
        }

    return None


def change_password(user_id: str, old_password: str, new_password: str) -> Dict[str, Any]:
    """
    Change a user's password.

    Args:
        user_id: User identifier
        old_password: Current password
        new_password: New password

    Returns:
        Dict with status
    """
    if user_id not in _users_store:
        return {'status': 'error', 'message': 'User not found'}

    user = _users_store[user_id]

    # Verify old password
    if not _verify_password(
        old_password,
        user.get('password_hash', ''),
        user.get('password_salt', '')
    ):
        return {'status': 'error', 'message': 'Invalid current password'}

    # Set new password
    hashed, salt = _hash_password(new_password)
    user['password_hash'] = hashed
    user['password_salt'] = salt
    user['password_changed_at'] = datetime.now().isoformat()

    logger.info(f"Password changed for user: {user_id}")
    return {'status': 'success', 'message': 'Password changed'}


def get_user(user_id: str) -> Optional[Dict]:
    """Get user by ID (without password data)."""
    if user_id in DEMO_USERS:
        return {**DEMO_USERS[user_id], 'id': user_id, 'demo': True}

    if user_id in _users_store:
        user = _users_store[user_id]
        return {
            'id': user_id,
            'name': user['name'],
            'email': user['email'],
            'role': user['role'],
            'active': user.get('active', True),
            'created_at': user.get('created_at')
        }

    return None


def list_users() -> List[Dict]:
    """List all users."""
    users = []

    # Add demo users
    for user_id, user_data in DEMO_USERS.items():
        users.append({
            'id': user_id,
            **user_data,
            'demo': True
        })

    # Add production users
    for user_id, user_data in _users_store.items():
        users.append({
            'id': user_id,
            'name': user_data['name'],
            'email': user_data['email'],
            'role': user_data['role'],
            'active': user_data.get('active', True),
            'demo': False
        })

    return users


def deactivate_user(user_id: str) -> Dict[str, Any]:
    """Deactivate a user (soft delete)."""
    if user_id in DEMO_USERS:
        return {'status': 'error', 'message': 'Cannot deactivate demo users'}

    if user_id not in _users_store:
        return {'status': 'error', 'message': 'User not found'}

    _users_store[user_id]['active'] = False
    logger.info(f"User deactivated: {user_id}")
    return {'status': 'success', 'message': 'User deactivated'}


# User roles
USER_ROLES = {
    'bd': 'Business Development',
    'compliance': 'Compliance Officer',
    'mlro': 'Money Laundering Reporting Officer',
    'admin': 'Administrator'
}
