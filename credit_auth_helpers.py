# Description: This file contains the helper functions for the credit authentication service.

# Example backend storage for credits (in-memory, for demonstration purposes)
credits_db = {
    'john_doeasu': {'key': 'johns_keyasu', 'credits': 100}, 
    'yash_asu': {'key': 'yash_keyasu', 'credits': 200}
}

def check_and_deduct_credits(name, key, duration):
    # Check if the name is in the credits database
    if name in credits_db and credits_db[name]['key'] == key:
        # Check if the user has enough credits
        if credits_db[name]['credits'] >= duration:
            # Deduct the credits
            credits_db[name]['credits'] -= duration
            return True, "Credits deducted successfully."
        else:
            return False, "Not enough credits."
    else:
        return False, "Invalid name or key."   