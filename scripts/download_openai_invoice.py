"""
OpenAI Invoice Downloader
Automatically downloads the latest invoice from OpenAI billing portal.

Usage:
    - As GitHub Action: credentials from environment variables
    - Locally: credentials from AWS Secrets Manager or .env file
"""

import os
import json
from datetime import datetime
from pathlib import Path

try:
    import boto3
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


def get_credentials():
    """
    Get credentials from environment variables or AWS Secrets Manager.
    Priority: ENV vars > AWS Secrets Manager
    """
    # Try environment variables first (GitHub Actions)
    email = os.environ.get('OPENAI_EMAIL')
    password = os.environ.get('OPENAI_PASSWORD')
    
    if email and password:
        print("✓ Using credentials from environment variables")
        return {'email': email, 'password': password}
    
    # Fall back to AWS Secrets Manager
    if HAS_BOTO3:
        try:
            secret_name = os.environ.get('AWS_SECRET_NAME', 'catholically/openai')
            region = os.environ.get('AWS_REGION', 'eu-south-1')
            
            client = boto3.client('secretsmanager', region_name=region)
            response = client.get_secret_value(SecretId=secret_name)
            print(f"✓ Using credentials from AWS Secrets Manager ({secret_name})")
            return json.loads(response['SecretString'])
        except Exception as e:
            print(f"⚠ AWS Secrets Manager error: {e}")
    
    raise ValueError(
        "No credentials found. Set OPENAI_EMAIL and OPENAI_PASSWORD "
        "environment variables or configure AWS Secrets Manager."
    )


def download_openai_invoice(output_dir: str = '/tmp/invoices', headless: bool = True):
    """
    Login to OpenAI and download the latest invoice.
    
    Args:
        output_dir: Directory to save the invoice PDF
        headless: Run browser in headless mode (set False for debugging)
    
    Returns:
        Path to the downloaded invoice file
    """
    creds = get_credentials()
    
    # Ensure output directory exists
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"📁 Output directory: {output_path.absolute()}")
    
    with sync_playwright() as p:
        print("🚀 Launching browser...")
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            accept_downloads=True,
            viewport={'width': 1280, 'height': 720}
        )
        page = context.new_page()
        
        try:
            # Step 1: Go to OpenAI login
            print("🔐 Navigating to OpenAI login...")
            page.goto('https://platform.openai.com/login', wait_until='networkidle')
            page.wait_for_timeout(2000)  # Wait for page to stabilize
            
            # Step 2: Click "Continue with email" or enter email directly
            # OpenAI's login flow may vary, handle both cases
            try:
                # Try clicking "Log in" first if on landing page
                login_button = page.locator('button:has-text("Log in"), a:has-text("Log in")')
                if login_button.count() > 0:
                    login_button.first.click()
                    page.wait_for_timeout(2000)
            except:
                pass
            
            # Look for email input or "Continue with email" button
            email_input = page.locator('input[name="email"], input[type="email"], input[id="email"]')
            
            if email_input.count() == 0:
                # Try clicking "Continue with email" button
                continue_email = page.locator('button:has-text("Continue with email")')
                if continue_email.count() > 0:
                    continue_email.click()
                    page.wait_for_timeout(1000)
                    email_input = page.locator('input[name="email"], input[type="email"]')
            
            # Step 3: Enter email
            print(f"📧 Entering email: {creds['email'][:3]}***")
            email_input.first.fill(creds['email'])
            
            # Click continue/next button
            continue_btn = page.locator('button:has-text("Continue"), button:has-text("Next"), button[type="submit"]')
            continue_btn.first.click()
            page.wait_for_timeout(2000)
            
            # Step 4: Enter password
            print("🔑 Entering password...")
            password_input = page.locator('input[name="password"], input[type="password"]')
            password_input.first.fill(creds['password'])
            
            # Click login/continue button
            login_btn = page.locator('button:has-text("Continue"), button:has-text("Log in"), button[type="submit"]')
            login_btn.first.click()
            
            # Step 5: Wait for login to complete
            print("⏳ Waiting for login to complete...")
            try:
                page.wait_for_url('**/platform.openai.com/**', timeout=30000)
            except PlaywrightTimeout:
                # Check if there's a 2FA or additional verification
                if 'verify' in page.url.lower() or 'mfa' in page.url.lower():
                    raise Exception(
                        "2FA/MFA detected. Please disable 2FA for automated access "
                        "or use an API key instead."
                    )
                raise
            
            page.wait_for_timeout(3000)  # Additional wait for page to load
            print("✓ Login successful!")
            
            # Step 6: Navigate to billing history
            print("💳 Navigating to billing history...")
            page.goto(
                'https://platform.openai.com/settings/organization/billing/history',
                wait_until='networkidle'
            )
            page.wait_for_timeout(3000)
            
            # Step 7: Find and download the latest invoice
            print("📄 Looking for invoices...")
            
            # Take a screenshot for debugging
            screenshot_path = output_path / 'billing_page.png'
            page.screenshot(path=str(screenshot_path))
            print(f"📸 Screenshot saved: {screenshot_path}")
            
            # Look for invoice download links/buttons
            # OpenAI typically has a table with PDF download links
            pdf_links = page.locator('a:has-text("PDF"), a:has-text("Download"), button:has-text("PDF")')
            
            if pdf_links.count() == 0:
                # Try looking for invoice rows with download options
                invoice_rows = page.locator('[data-testid="invoice-row"], tr:has(td)')
                print(f"Found {invoice_rows.count()} potential invoice rows")
                
                # Look for any download icon or link
                pdf_links = page.locator('a[href*="invoice"], a[href*="pdf"], a[download]')
            
            if pdf_links.count() > 0:
                print(f"✓ Found {pdf_links.count()} invoice download link(s)")
                
                # Download the first (latest) invoice
                with page.expect_download(timeout=30000) as download_info:
                    pdf_links.first.click()
                
                download = download_info.value
                
                # Generate filename with date
                invoice_name = f"openai_invoice_{datetime.now().strftime('%Y%m')}.pdf"
                invoice_path = output_path / invoice_name
                
                download.save_as(str(invoice_path))
                print(f"✓ Invoice downloaded: {invoice_path}")
                
                return str(invoice_path)
            else:
                print("⚠ No invoice download links found on the page")
                print("  This could mean:")
                print("  - No invoices available yet")
                print("  - Page structure has changed")
                print("  - Check the screenshot for details")
                return None
                
        except Exception as e:
            # Save screenshot on error for debugging
            error_screenshot = output_path / 'error_screenshot.png'
            page.screenshot(path=str(error_screenshot))
            print(f"❌ Error occurred. Screenshot saved: {error_screenshot}")
            raise
            
        finally:
            browser.close()
            print("🏁 Browser closed")


def upload_to_s3(file_path: str, bucket: str, prefix: str = 'invoices/openai/'):
    """
    Upload the invoice to S3.
    
    Args:
        file_path: Path to the file to upload
        bucket: S3 bucket name
        prefix: S3 key prefix (folder path)
    """
    if not HAS_BOTO3:
        print("⚠ boto3 not installed, skipping S3 upload")
        return None
    
    s3 = boto3.client('s3')
    file_name = Path(file_path).name
    s3_key = f"{prefix}{file_name}"
    
    print(f"☁️ Uploading to s3://{bucket}/{s3_key}...")
    s3.upload_file(file_path, bucket, s3_key)
    print(f"✓ Upload complete!")
    
    return f"s3://{bucket}/{s3_key}"


def main():
    """Main entry point."""
    print("=" * 50)
    print("OpenAI Invoice Downloader")
    print("=" * 50)
    print()
    
    # Configuration from environment
    output_dir = os.environ.get('OUTPUT_DIR', '/tmp/invoices')
    headless = os.environ.get('HEADLESS', 'true').lower() == 'true'
    s3_bucket = os.environ.get('S3_BUCKET')
    
    try:
        # Download invoice
        invoice_path = download_openai_invoice(
            output_dir=output_dir,
            headless=headless
        )
        
        if invoice_path and s3_bucket:
            # Upload to S3 if bucket is configured
            upload_to_s3(invoice_path, s3_bucket)
        
        print()
        print("=" * 50)
        print("✅ Done!")
        print("=" * 50)
        
    except Exception as e:
        print()
        print("=" * 50)
        print(f"❌ Failed: {e}")
        print("=" * 50)
        raise


if __name__ == '__main__':
    main()
