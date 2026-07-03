import datetime
from database import db
from security import encrypt_secret
from integration_routes import sync_all_integrations
import asyncio

async def test_refresh():
    tenant_id = "t-acme"
    provider = "gmail"
    
    # Manually set an expired token
    expired_expiry = (datetime.datetime.now() - datetime.timedelta(minutes=10)).isoformat()
    config = {
        "connected_at": datetime.datetime.now().isoformat(),
        "access_token": encrypt_secret("old-expired-token"),
        "refresh_token": encrypt_secret("valid-refresh-token"),
        "token_expiry": expired_expiry,
        "settings": {"enabled": True}
    }
    db.connected_integrations[tenant_id][provider] = config
    
    print(f"Initial expiry: {expired_expiry}")
    
    # Trigger sync (which should trigger refresh)
    await sync_all_integrations(tenant_id)
    
    # Check if token was refreshed
    new_config = db.get_integration_config(tenant_id, provider)
    new_expiry = new_config.get("token_expiry")
    print(f"New expiry: {new_expiry}")
    
    if new_expiry > expired_expiry:
        print("SUCCESS: Token was refreshed during sync.")
    else:
        print("FAILURE: Token was NOT refreshed.")

if __name__ == "__main__":
    asyncio.run(test_refresh())
