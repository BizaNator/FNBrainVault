

Toggle Light / Dark / Auto color theme

Toggle table of contents sidebar

Quickstart guide[#](#quickstart-guide "Link to this heading")
=============================================================

Installation[#](#installation "Link to this heading")
-----------------------------------------------------

Since it’s a part of undetected-chromedriver, installation goes via

\# todo. use pip install nodriver instead
pip install undetected\-chromedriver

* * *

Or as a seperate package via:

pip install nodriver

usage example[#](#usage-example "Link to this heading")
=======================================================

The aim of this project (just like undetected-chromedriver, somewhere long ago) is to keep it short and simple, so you can quickly open an editor or interactive session, type or paste a few lines and off you go.

import nodriver as uc

async def main():

    browser \= await uc.start()
    page \= await browser.get('https://www.nowsecure.nl')

    ... further code ...

if \_\_name\_\_ \== '\_\_main\_\_':
    \# since asyncio.run never worked (for me)
    uc.loop().run\_until\_complete(main())

More complete example[#](#more-complete-example "Link to this heading")
=======================================================================

import nodriver

async def main():

    browser \= await nodriver.start()
    page \= await browser.get('https://www.nowsecure.nl')

    await page.save\_screenshot()
    await page.get\_content()
    await page.scroll\_down(150)
    elems \= await page.select\_all('\*\[src\]')

    for elem in elems:
        await elem.flash()

    page2 \= await browser.get('https://twitter.com', new\_tab\=True)
    page3 \= await browser.get('https://github.com/ultrafunkamsterdam/nodriver', new\_window\=True)

    for p in (page, page2, page3):
       await p.bring\_to\_front()
       await p.scroll\_down(200)
       await p   \# wait for events to be processed
       await p.reload()
       if p != page3:
           await p.close()

if \_\_name\_\_ \== '\_\_main\_\_':

    \# since asyncio.run never worked (for me)
    uc.loop().run\_until\_complete(main())

Custom starting options[#](#custom-starting-options "Link to this heading")
===========================================================================

I’ll leave out the async boilerplate here

from nodriver import \*

browser \= await start(
    headless\=False,
    user\_data\_dir\="/path/to/existing/profile",  \# by specifying it, it won't be automatically cleaned up when finished
    browser\_executable\_path\="/path/to/some/other/browser",
    browser\_args\=\['--some-browser-arg=true', '--some-other-option'\],
    lang\="en-US"   \# this could set iso-language-code in navigator, not recommended to change
)
tab \= await browser.get('https://somewebsite.com')

Alternative custom options[#](#alternative-custom-options "Link to this heading")
=================================================================================

I’ll leave out the async boilerplate here

from nodriver import \*

config \= Config()
config.headless \= False
config.user\_data\_dir\="/path/to/existing/profile",  \# by specifying it, it won't be automatically cleaned up when finished
config.browser\_executable\_path\="/path/to/some/other/browser",
config.browser\_args\=\['--some-browser-arg=true', '--some-other-option'\],
config.lang\="en-US"   \# this could set iso-language-code in navigator, not recommended to change
)

A more concrete example, which can be found in the ./example/ folder, shows a script to create a twitter account

import asyncio
import random
import string
import logging

logging.basicConfig(level\=30)

import nodriver as uc

months \= \[
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
\]

async def main():
    driver \= await uc.start()

    tab \= await driver.get("https://twitter.com")

    \# wait for text to appear instead of a static number of seconds to wait
    \# this does not always work as expected, due to speed.
    print('finding the "create account" button')
    create\_account \= await tab.find("create account", best\_match\=True)

    print('"create account" => click')
    await create\_account.click()

    print("finding the email input field")
    email \= await tab.select("input\[type=email\]")

    \# sometimes, email field is not shown, because phone is being asked instead
    \# when this occurs, find the small text which says "use email instead"
    if not email:
        use\_mail\_instead \= await tab.find("use email instead")
        \# and click it
        await use\_mail\_instead.click()

        \# now find the email field again
        email \= await tab.select("input\[type=email\]")

    randstr \= lambda k: "".join(random.choices(string.ascii\_letters, k\=k))

    \# send keys to email field
    print('filling in the "email" input field')
    await email.send\_keys("".join(\[randstr(8), "@", randstr(8), ".com"\]))

    \# find the name input field
    print("finding the name input field")
    name \= await tab.select("input\[type=text\]")

    \# again, send random text
    print('filling in the "name" input field')
    await name.send\_keys(randstr(8))

    \# since there are 3 select fields on the tab, we can use unpacking
    \# to assign each field
    print('finding the "month" , "day" and "year" fields in 1 go')
    sel\_month, sel\_day, sel\_year \= await tab.select\_all("select")

    \# await sel\_month.focus()
    print('filling in the "month" input field')
    await sel\_month.send\_keys(months\[random.randint(0, 11)\].title())

    \# await sel\_day.focus()
    \# i don't want to bother with month-lengths and leap years
    print('filling in the "day" input field')
    await sel\_day.send\_keys(str(random.randint(0, 28)))

    \# await sel\_year.focus()
    \# i don't want to bother with age restrictions
    print('filling in the "year" input field')
    await sel\_year.send\_keys(str(random.randint(1980, 2005)))

    await tab

    \# let's handle the cookie nag as well
    cookie\_bar\_accept \= await tab.find("accept all", best\_match\=True)
    if cookie\_bar\_accept:
        await cookie\_bar\_accept.click()

    await tab.sleep(1)

    next\_btn \= await tab.find(text\="next", best\_match\=True)
    \# for btn in reversed(next\_btns):
    await next\_btn.mouse\_click()

    print("sleeping 2 seconds")
    await tab.sleep(2)  \# visually see what part we're actually in

    print('finding "next" button')
    next\_btn \= await tab.find(text\="next", best\_match\=True)
    print('clicking "next" button')
    await next\_btn.mouse\_click()

    \# just wait for some button, before we continue
    await tab.select("\[role=button\]")

    print('finding "sign up"  button')
    sign\_up\_btn \= await tab.find("Sign up", best\_match\=True)
    \# we need the second one
    print('clicking "sign up"  button')
    await sign\_up\_btn.click()

    print('the rest of the "implementation" is out of scope')
    \# further implementation outside of scope
    await tab.sleep(10)
    driver.stop()

    \# verification code per mail

if \_\_name\_\_ \== "\_\_main\_\_":
    \# since asyncio.run never worked (for me)
    \# i use
    uc.loop().run\_until\_complete(main())

[

Next

Browser class

](classes/browser.html)[

Previous

Home

