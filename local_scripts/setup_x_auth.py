import asyncio
from twikit import Client
import os

async def main():
    print("--- X (Twitter) Authentication Setup ---")
    print("This script will log you into X and save your session cookies.")
    print("Use a BURNER account for this project.")
    
    username = input("Enter X Username: ")
    email = input("Enter X Email: ")
    password = input("Enter X Password: ")

    client = Client('en-US')

    try:
        print("\nAttempting login...")
        await client.login(
            auth_info_1=username,
            auth_info_2=email,
            password=password
        )
        
        # Save cookies to a local file
        # We save it to .x_cookies (ensure this is in .gitignore)
        client.save_cookies('x_cookies.json')
        print("\n[SUCCESS] Cookies saved to 'x_cookies.json'!")
        print("Your scraper can now use these cookies to fetch data autonomously.")
        
    except Exception as e:
        print(f"\n[ERROR] Login failed: {e}")
        print("Check your credentials and try again. If you have 2FA enabled, you may need to disable it for the initial login.")

if __name__ == "__main__":
    asyncio.run(main())
