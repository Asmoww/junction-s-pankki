"""One continuous take of the live S-Pankki app (Emma), recorded from the browser's screencast at 2x device pixels.
Login happens in a separate context before recording; no mocks, no prerecorded replies."""
import asyncio, base64, json, os, subprocess, time
from playwright.async_api import async_playwright

FF = "/home/psavela/.cache/ms-playwright/ffmpeg-1013/ffmpeg-linux"
URL = "https://spankki.psavela.com"
LOG, FRAMES = [], []
T0 = None


def mark(what, **extra):
    LOG.append({"t": round(time.time() - T0, 2), "action": what, **extra}); print(LOG[-1], flush=True)


async def main():
    global T0
    async with async_playwright() as pw:
        b = await pw.chromium.launch(executable_path="/home/psavela/.local/bin/google-chrome", args=["--headless=new", "--no-sandbox"])
        auth = await b.new_context(); a = await auth.new_page()          # log in outside the footage
        await a.goto(f"{URL}/login"); await a.fill("input[name=password]", os.environ["DEMO_PASSWORD"]); await a.press("input[name=password]", "Enter")
        await a.wait_for_timeout(1500); state = await auth.storage_state(); await auth.close()
        ctx = await b.new_context(viewport={"width": 430, "height": 932}, device_scale_factor=2, has_touch=True, storage_state=state,
                                  record_video_dir="/tmp/capture/raw", record_video_size={"width": 430, "height": 932})
        p = await ctx.new_page(); errs = []; p.on("pageerror", lambda e: errs.append(str(e)))
        await p.add_init_script("localStorage.setItem('lang', 'en')")
        T0 = time.time()   # the recording starts with the page
        await p.goto(f"{URL}/"); mark("app open: customer picker")
        await p.wait_for_selector("text=Emma"); await p.wait_for_timeout(1800)
        await p.get_by_text("Emma", exact=True).click(); mark("pick demo customer Emma")
        await p.wait_for_selector("#g svg"); await p.wait_for_timeout(6000)
        mark("home baseline shown", payday=(await p.inner_text(".result")).replace("\n", " "))
        await p.click("#tabbar button[data-tab=coach]"); await p.wait_for_timeout(1200); mark("open Coach")
        q = "Why am I always short before payday?"
        await p.click("#q"); await p.type("#q", q, delay=70); mark("typed question", text=q)
        await p.wait_for_timeout(500); await p.press("#q", "Enter"); mark("sent question")
        await p.wait_for_selector(".msg.bot .vbadge", timeout=180000)
        mark("answer returned", badge=await p.locator(".vbadge").last.inner_text())
        await p.wait_for_timeout(3500)
        how = p.locator("#thread .msg:last-child details.how summary").first
        await how.scroll_into_view_if_needed(timeout=8000); await p.wait_for_timeout(800); await how.click(); mark("opened 'How I worked this out'")
        await p.wait_for_timeout(1200); await p.locator("#thread .msg:last-child details.how").first.scroll_into_view_if_needed(timeout=8000)
        await p.wait_for_timeout(4000)
        await p.click("#tabbar button[data-tab=home]"); await p.wait_for_timeout(1500); mark("back to Home")
        await p.locator("[data-sc=pause]").scroll_into_view_if_needed(); await p.mouse.wheel(0, -260); await p.wait_for_timeout(1500)
        await p.click("[data-sc=pause]"); mark("tap Pause extras"); await p.wait_for_timeout(3000)
        mark("redrawn", payday=(await p.inner_text(".result")).replace("\n", " "))
        await p.click("[data-sc=rent]"); mark("tap Rent after payday (both changes combined)"); await p.wait_for_timeout(3500)
        mark("redrawn", payday=(await p.inner_text(".result")).replace("\n", " "))
        await p.click("#tabbar button[data-tab=learn]"); await p.wait_for_timeout(1500); mark("open Learn")
        await p.wait_for_timeout(1500); mark("Money Detective map", progress=await p.inner_text("#detective .big"))
        await p.wait_for_timeout(4000)
        await p.click("#tabbar button[data-tab=home]"); await p.wait_for_timeout(1500)
        await p.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})"); await p.wait_for_timeout(1200)
        await p.click("[data-rng='12']"); mark("tap 12 months"); await p.wait_for_timeout(5000); mark("year view shown")
        await p.click("[data-rng='pay']"); mark("back to pay month"); await p.wait_for_timeout(2500); mark("end")
        vid = await p.video.path(); await ctx.close(); await b.close()
    import shutil; shutil.move(str(vid), "/tmp/capture/emma-live-flow.webm")
    json.dump({"actions": LOG, "errors": errs}, open("/tmp/capture/actions.json", "w"), indent=1, ensure_ascii=False)
    print("errors:", errs)

asyncio.run(main())
