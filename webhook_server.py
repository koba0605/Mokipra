import os
import stripe
import logging
from fastapi import FastAPI, Request, HTTPException
from supabase import create_client, Client

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
app = FastAPI()

PLAN_WEIGHTS = {"Free": 0, "Pro": 1, "Max": 2}

@app.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except ValueError:
        logger.error("Invalid payload received.")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        logger.error("Invalid signature detected.")
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        user_id = session.get('client_reference_id')
        
        metadata = session.get('metadata', {})
        new_plan = metadata.get('plan')

        if not new_plan:
            amount = session.get('amount_total')
            currency = session.get('currency', 'jpy').lower()
            if currency == 'jpy' or currency == 'usd':
                new_plan = "Pro" if amount == 480 else "Max" if amount == 980 else "Free"
            else:
                new_plan = "Free"

        if user_id and new_plan in PLAN_WEIGHTS:
            try:
                result = supabase.rpc('update_plan_atomic', {
                    'target_user_id': user_id,
                    'new_plan': new_plan,
                    'new_weight': PLAN_WEIGHTS[new_plan]
                }).execute()
                
                if result.data:
                    plan_result = result.data
                    action = plan_result.get('action', 'unknown')
                    logger.info(f"Plan update result: user={user_id}, action={action}, plan={new_plan}")
                else:
                    logger.error("No data returned from RPC")
                    
            except Exception as e:
                logger.error(f"❌ RPC failed for user {user_id}: {e}")

    return {"status": "success"}