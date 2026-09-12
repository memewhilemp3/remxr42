"""
remxr42 Command Line Interface
Launches the remxr42 dual turntable workstation.
"""

import os
import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description="remxr42 - Dual Circular Polar Vinyl DJ Workstation")
    parser.add_argument("--port", "-p", type=int, default=8542, help="Port to run the workstation on (default: 8542)")
    parser.add_argument("--browser", "-b", action="store_true", default=True, help="Open browser automatically")
    parser.add_argument("--web-only", action="store_true", help="Open the Zero-Install standalone HTML edition directly in default browser")
    args, unknown = parser.parse_known_args()

    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    
    if args.web_only:
        import webbrowser
        # Try local or root remxr42.html
        html_candidates = [
            os.path.join(pkg_dir, "remxr42.html"),
            os.path.join(os.path.dirname(os.path.dirname(pkg_dir)), "remxr42.html")
        ]
        target_html = next((h for h in html_candidates if os.path.exists(h)), None)
        if target_html:
            print(f"Opening Zero-Install Standalone Web Edition: {target_html}")
            webbrowser.open("file://" + os.path.abspath(target_html))
            return
        else:
            print("remxr42.html not found, falling back to Streamlit app...")

    app_path = os.path.join(pkg_dir, "app.py")
    if not os.path.exists(app_path):
        app_path = os.path.join(os.path.dirname(pkg_dir), "app.py")

    from streamlit.web import cli as stcli
    st_args = [
        "streamlit",
        "run",
        app_path,
        "--server.port", str(args.port),
        "--server.headless", "false" if args.browser else "true",
        "--browser.serverAddress", "localhost",
        "--server.enableCORS", "false"
    ]
    if unknown:
        st_args.extend(unknown)

    sys.argv = st_args
    print(f"\n" + "="*60)
    print("  remxr42 // DUAL CIRCULAR POLAR VINYL WORKSTATION")
    print(f"  Starting local server at: http://localhost:{args.port}")
    print("="*60 + "\n")
    sys.exit(stcli.main())

if __name__ == "__main__":
    main()
