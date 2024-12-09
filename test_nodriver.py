import nodriver as uc
import asyncio

async def main():
    try:
        browser = await uc.start()
        page = await browser.get('https://dev.epicgames.com/documentation/en-us/uefn/unreal-editor-for-fortnite-documentation')
        content = await page.get_content()
        print("Browser started successfully.")
        await browser.stop()
    except Exception as e:
        print(f"Error starting browser: {e}")

if __name__ == "__main__":
    asyncio.run(main())