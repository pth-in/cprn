import httpx
import json
import os
import re
from dotenv import load_dotenv

load_dotenv()

def get_twitter_headers(auth_token, ct0):
    return {
        "authority": "x.com",
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwSDRsSxx9YD3u92y69bc7Y6n%2B%2B79v3dr2%2B9%2B7j%2B1%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2B%2BI",
        "cookie": f"auth_token={auth_token}; ct0={ct0}",
        "referer": "https://x.com/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "x-csrf-token": ct0,
        "x-twitter-active-user": "yes",
        "x-twitter-auth-type": "OAuth2Session",
        "x-twitter-client-language": "en"
    }

async def fetch_tweet_raw(tweet_id):
    # We retrieve the latest cookies from Supabase
    from supabase import create_client
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SECRET_KEY")
    supabase = create_client(url, key)
    
    res = supabase.table("social_accounts").select("cookies_json").eq("username", "jaiappo").single().execute()
    cookies_list = json.loads(res.data['cookies_json'])
    
    auth_token = next(c['value'] for c in cookies_list if c['name'] == 'auth_token')
    ct0 = next(c['value'] for c in cookies_list if c['name'] == 'ct0')

    headers = get_twitter_headers(auth_token, ct0)
    
    # GraphQL Query for Tweet Detail
    # This is a common query ID for TweetDetail
    query_id = "0BT7sir9f7SvYru9S96f_w"
    variables = {
        "focalTweetId": tweet_id,
        "with_rux_injections": False,
        "includePromotedContent": True,
        "withCommunity": True,
        "withQuickPromoteEligibilityQueries": True,
        "withBirdwatchNotes": True,
        "withVoice": True,
        "withV2Timeline": True
    }
    features = {
        "responsive_web_graphql_exclude_directive_enabled": True,
        "verified_phone_label_enabled": False,
        "creator_subscriptions_tweet_preview_api_enabled": True,
        "responsive_web_graphql_timeline_navigation_enabled": True,
        "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
        "c9s_tweet_anatomy_moderator_badge_enabled": True,
        "tweetypie_unmention_optimization_enabled": True,
        "responsive_web_edit_tweet_api_enabled": True,
        "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
        "view_counts_everywhere_api_enabled": True,
        "longform_notetweets_viewer_api_enabled": True,
        "tweet_awards_web_tipping_enabled": False,
        "freedom_of_speech_not_reach_fetch_enabled": True,
        "standardized_nudges_misinfo": True,
        "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
        "rweb_video_timestamps_enabled": True,
        "detailed_replies_viewer_api_enabled": True,
        "units_2024_01_enabled": True,
        "responsive_web_enhance_cards_enabled": False
    }

    url = f"https://x.com/i/api/graphql/{query_id}/TweetDetail"
    params = {
        "variables": json.dumps(variables),
        "features": json.dumps(features)
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            # Navigate to tweet text
            # This is complex in GraphQL, usually deep in instructions
            return data
        else:
            print(f"[ERROR] Fetch failed: {response.status_code}")
            print(response.text[:500])
            return None

import asyncio
if __name__ == "__main__":
    t_id = "2017816585826926812" # User's ID
    res = asyncio.run(fetch_tweet_raw(t_id))
    if res:
        print(json.dumps(res, indent=2)[:2000] + "...")
