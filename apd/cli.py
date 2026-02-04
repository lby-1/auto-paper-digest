"""
CLI module for Auto Paper Digest.

Provides commands for fetching papers, downloading PDFs,
running NotebookLM automation, and generating digests.
"""

import sys
import io

# Fix encoding for Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from pathlib import Path
from typing import Optional

import click

from . import __version__
from .config import Status, ensure_directories
from .db import count_papers, get_paper, init_db, list_papers
from .utils import get_current_week_id, get_logger, setup_logging


# =============================================================================
# CLI Group
# =============================================================================

@click.group()
@click.version_option(version=__version__, prog_name="apd")
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug logging"
)
@click.pass_context
def main(ctx: click.Context, debug: bool) -> None:
    """
    Auto Paper Digest - Fetch HF papers, generate NotebookLM video overviews.
    
    Run 'apd COMMAND --help' for more information on a command.
    """
    ctx.ensure_object(dict)
    
    # Setup logging
    level = "DEBUG" if debug else "INFO"
    setup_logging(level=level)
    
    # Initialize database and directories
    ensure_directories()
    init_db()


# =============================================================================
# Fetch Command
# =============================================================================

@main.command()
@click.option(
    "--week", "-w",
    default=None,
    help="Week ID (e.g., 2026-01). Defaults to current week if no --date specified."
)
@click.option(
    "--date", "-d",
    default=None,
    help="Date (e.g., 2026-01-08). Fetch papers for a specific date."
)
@click.option(
    "--max", "-m",
    "max_papers",
    default=50,
    type=int,
    help="Maximum papers to fetch (default: 50)"
)
def fetch(week: Optional[str], date: Optional[str], max_papers: int) -> None:
    """
    Fetch papers from Hugging Face for a given week or date.
    
    Use --week for weekly papers or --date for a specific date.
    If neither is specified, defaults to current week.
    
    Note: Some dates (weekends/holidays) have no papers. If you specify
    a date with no papers, an error will be shown.
    """
    from .hf_fetcher import fetch_daily_papers, fetch_weekly_papers
    
    logger = get_logger()
    
    # Validate mutually exclusive options
    if week and date:
        click.echo("❌ Error: --week and --date are mutually exclusive. Use one or the other.", err=True)
        sys.exit(1)
    
    try:
        if date:
            # Date-based fetching
            click.echo(f"📚 Fetching papers for date {date}...")
            papers = fetch_daily_papers(date, max_papers=max_papers)
            click.echo(f"✅ Fetched {len(papers)} papers")
            
            # Show stats
            total = count_papers(week_id=date)
            click.echo(f"   Total papers in database for {date}: {total}")
        else:
            # Week-based fetching (default)
            week_id = week or get_current_week_id()
            click.echo(f"📚 Fetching papers for week {week_id}...")
            papers = fetch_weekly_papers(week_id, max_papers=max_papers)
            click.echo(f"✅ Fetched {len(papers)} papers")
            
            # Show stats
            total = count_papers(week_id=week_id)
            click.echo(f"   Total papers in database for {week_id}: {total}")
        
    except ValueError as e:
        # Date has no papers (redirect detected)
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        logger.exception("Fetch failed")
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


# =============================================================================
# Download Command
# =============================================================================

@main.command()
@click.option(
    "--week", "-w",
    default=None,
    help="Week ID (e.g., 2026-01). Defaults to current week."
)
@click.option(
    "--paper-id", "-p",
    default=None,
    help="Download a specific paper by ID"
)
@click.option(
    "--force", "-f",
    is_flag=True,
    help="Force re-download even if PDF exists"
)
@click.option(
    "--max", "-m",
    "max_papers",
    default=None,
    type=int,
    help="Maximum papers to download"
)
def download(
    week: Optional[str],
    paper_id: Optional[str],
    force: bool,
    max_papers: Optional[int]
) -> None:
    """
    Download PDFs from arXiv for fetched papers.
    
    Downloads are idempotent - existing files with matching
    SHA256 hashes will be skipped unless --force is used.
    """
    from .pdf_downloader import download_pdfs_for_week, download_single_paper
    
    logger = get_logger()
    
    try:
        if paper_id:
            # Download single paper
            click.echo(f"📄 Downloading PDF for paper {paper_id}...")
            result = download_single_paper(paper_id, force=force)
            if result:
                click.echo(f"✅ Downloaded: {result}")
            else:
                click.echo("❌ Download failed", err=True)
                sys.exit(1)
        else:
            # Download all papers for week
            week_id = week or get_current_week_id()
            click.echo(f"📄 Downloading PDFs for week {week_id}...")
            
            success, failure = download_pdfs_for_week(
                week_id, force=force, max_papers=max_papers
            )
            
            click.echo(f"✅ Downloads complete: {success} success, {failure} failed")
            
    except Exception as e:
        logger.exception("Download failed")
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


# =============================================================================
# NotebookLM Command
# =============================================================================

@main.command()
@click.option(
    "--week", "-w",
    default=None,
    help="Week ID (e.g., 2026-01). Defaults to current week."
)
@click.option(
    "--paper-id", "-p",
    default=None,
    help="Process a specific paper by ID"
)
@click.option(
    "--headful",
    is_flag=True,
    help="Run browser in visible mode (required for first-time login)"
)
@click.option(
    "--force", "-f",
    is_flag=True,
    help="Force reprocessing even if already done"
)
@click.option(
    "--max", "-m",
    "max_papers",
    default=None,
    type=int,
    help="Maximum papers to process"
)
@click.option(
    "--prompt",
    default=None,
    help="Steering prompt for video generation"
)
def nblm(
    week: Optional[str],
    paper_id: Optional[str],
    headful: bool,
    force: bool,
    max_papers: Optional[int],
    prompt: Optional[str]
) -> None:
    """
    Process papers through NotebookLM.
    
    Creates notebooks, uploads PDFs, generates Audio Overview videos,
    and downloads them locally.
    
    First-time usage requires --headful for manual Google login.
    Subsequent runs can be headless (the session is persisted).
    """
    from pathlib import Path
    from .nblm_bot import NotebookLMBot, process_papers_for_week
    
    logger = get_logger()
    headless = not headful
    
    try:
        if paper_id:
            # Process single paper
            paper = get_paper(paper_id)
            if not paper:
                click.echo(f"❌ Paper not found: {paper_id}", err=True)
                sys.exit(1)
            
            if not paper.pdf_path:
                click.echo(f"❌ Paper has no PDF downloaded: {paper_id}", err=True)
                sys.exit(1)
            
            click.echo(f"🤖 Processing paper {paper_id} through NotebookLM...")
            
            with NotebookLMBot(headless=headless) as bot:
                result = bot.process_paper(
                    paper_id=paper_id,
                    pdf_path=Path(paper.pdf_path),
                    week_id=paper.week_id,
                    steering_prompt=prompt,
                    force=force
                )
            
            if result:
                click.echo(f"✅ Successfully processed paper {paper_id}")
            else:
                click.echo(f"❌ Failed to process paper {paper_id}", err=True)
                sys.exit(1)
        else:
            # Process all papers for week
            week_id = week or get_current_week_id()
            
            # Check how many papers are ready
            ready = count_papers(week_id=week_id, status=Status.PDF_OK)
            if ready == 0:
                click.echo(f"⚠️  No papers ready for NotebookLM processing in week {week_id}")
                click.echo("   Run 'apd download' first to download PDFs.")
                return
            
            click.echo(f"🤖 Processing {ready} papers for week {week_id}...")
            
            success, failure = process_papers_for_week(
                week_id=week_id,
                headless=headless,
                max_papers=max_papers,
                force=force,
                steering_prompt=prompt
            )
            
            click.echo(f"✅ Processing complete: {success} success, {failure} failed")
            
    except Exception as e:
        logger.exception("NotebookLM processing failed")
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


# =============================================================================
# Upload Command (Phase 1 of two-phase workflow)
# =============================================================================

@main.command()
@click.option(
    "--week", "-w",
    default=None,
    help="Week ID (e.g., 2026-01). Defaults to current week if no --date specified."
)
@click.option(
    "--date", "-d",
    default=None,
    help="Date (e.g., 2026-01-08). Process papers for a specific date."
)
@click.option(
    "--headful",
    is_flag=True,
    help="Run browser in visible mode (required for first-time login)"
)
@click.option(
    "--max", "-m",
    "max_papers",
    default=10,
    type=int,
    help="Maximum papers to process (default: 10)"
)
@click.option(
    "--force", "-f",
    is_flag=True,
    help="Force re-processing even if already done"
)
def upload(
    week: Optional[str],
    date: Optional[str],
    headful: bool,
    max_papers: int,
    force: bool
) -> None:
    """
    Phase 1: Fetch papers, download PDFs, upload to NotebookLM, trigger video generation.
    
    Use --week for weekly papers or --date for a specific date.
    
    Complete first phase of the two-phase workflow:
    1. Fetches papers from Hugging Face
    2. Downloads PDFs from arXiv
    3. Creates notebooks named {period_id}_{paper_id}
    4. Uploads PDF and waits for content to load
    5. Triggers video generation (doesn't wait for completion)
    
    After this completes, wait a few minutes for videos to generate,
    then run 'apd download-video' to download them.
    
    Use --force to re-process papers that have already been uploaded.
    """
    from .hf_fetcher import fetch_daily_papers, fetch_weekly_papers
    from .nblm_bot import upload_papers_for_week
    from .pdf_downloader import download_pdfs_for_week
    
    logger = get_logger()
    headless = not headful
    
    # Validate mutually exclusive options
    if week and date:
        click.echo("❌ Error: --week and --date are mutually exclusive. Use one or the other.", err=True)
        sys.exit(1)
    
    # Determine period_id (date or week)
    if date:
        period_id = date
        period_type = "date"
    else:
        period_id = week or get_current_week_id()
        period_type = "week"
    
    click.echo(f"🚀 Phase 1: Upload pipeline for {period_type} {period_id}")
    click.echo(f"   Max papers: {max_papers}")
    if force:
        click.echo(f"   Force mode: ON (will re-process already uploaded papers)")
    click.echo()
    
    try:
        # Step 1: Fetch papers
        click.echo("=" * 50)
        click.echo("📚 Step 1: Fetching papers from Hugging Face...")
        if date:
            papers = fetch_daily_papers(period_id, max_papers=max_papers)
        else:
            papers = fetch_weekly_papers(period_id, max_papers=max_papers)
        click.echo(f"   Fetched {len(papers)} papers")
        
        if not papers:
            click.echo(f"⚠️  No papers found for this {period_type}.")
            return
        
        # Step 2: Download PDFs
        click.echo()
        click.echo("=" * 50)
        click.echo("📄 Step 2: Downloading PDFs from arXiv...")
        dl_success, dl_failure = download_pdfs_for_week(
            period_id, force=force, max_papers=max_papers
        )
        click.echo(f"   Downloads: {dl_success} success, {dl_failure} failed")
        
        # Step 3: Upload to NotebookLM
        click.echo()
        click.echo("=" * 50)
        click.echo("📤 Step 3: Uploading to NotebookLM & triggering video generation...")
        click.echo(f"   Notebooks will be named: {period_id}_{{paper_id}}")
        
        success, failure = upload_papers_for_week(
            week_id=period_id,
            headless=headless,
            max_papers=max_papers,
            force=force
        )
        
        # Summary
        click.echo()
        click.echo("=" * 50)
        click.echo(f"✅ Phase 1 complete: {success} success, {failure} failed")
        if success > 0:
            click.echo()
            click.echo("💡 Videos are now generating in NotebookLM.")
            click.echo("   Wait a few minutes, then run:")
            if date:
                click.echo(f"   apd download-video --date {period_id}")
            else:
                click.echo(f"   apd download-video --week {period_id}")
            
    except ValueError as e:
        # Date has no papers (redirect detected)
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo("\n⚠️  Upload interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.exception("Upload failed")
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


# =============================================================================
# Download Video Command (Phase 2 of two-phase workflow)
# =============================================================================

@main.command("download-video")
@click.option(
    "--week", "-w",
    default=None,
    help="Week ID (e.g., 2026-01). Defaults to current week if no --date specified."
)
@click.option(
    "--date", "-d",
    default=None,
    help="Date (e.g., 2026-01-08). Download videos for a specific date."
)
@click.option(
    "--headful",
    is_flag=True,
    help="Run browser in visible mode"
)
@click.option(
    "--max", "-m",
    "max_papers",
    default=None,
    type=int,
    help="Maximum papers to process"
)
@click.option(
    "--force", "-f",
    is_flag=True,
    help="Force re-download even if video already exists"
)
def download_video(
    week: Optional[str],
    date: Optional[str],
    headful: bool,
    max_papers: Optional[int],
    force: bool
) -> None:
    """
    Download generated videos from NotebookLM.
    
    Use --week for weekly papers or --date for a specific date.
    
    Phase 2 of the two-phase workflow:
    1. Opens NotebookLM home page
    2. Finds notebooks with {period_id}_ prefix
    3. Checks if video is ready for each
    4. Downloads completed videos
    
    Run this after 'apd upload' and waiting for videos to generate.
    """
    from .nblm_bot import download_videos_for_week
    
    logger = get_logger()
    headless = not headful
    
    # Validate mutually exclusive options
    if week and date:
        click.echo("❌ Error: --week and --date are mutually exclusive. Use one or the other.", err=True)
        sys.exit(1)
    
    # Determine period_id (date or week)
    if date:
        period_id = date
        period_type = "date"
    else:
        period_id = week or get_current_week_id()
        period_type = "week"
    
    try:
        # Check how many papers are awaiting download
        awaiting = count_papers(week_id=period_id, status=Status.NBLM_OK)
        video_ok = count_papers(week_id=period_id, status=Status.VIDEO_OK)
        
        if awaiting == 0 and (video_ok == 0 or not force):
            click.echo(f"⚠️  No papers awaiting video download for {period_type} {period_id}")
            if video_ok > 0:
                click.echo(f"   ({video_ok} videos already downloaded. Use --force to re-download)")
            else:
                click.echo("   Run 'apd upload' first to upload PDFs to NotebookLM.")
            return
        
        total = awaiting + (video_ok if force else 0)
        click.echo(f"📥 Downloading videos for {total} papers in {period_type} {period_id}...")
        if force and video_ok > 0:
            click.echo(f"   (--force: will re-check {video_ok} already downloaded videos)")
        click.echo()
        
        success, failure, skipped = download_videos_for_week(
            week_id=period_id,
            headless=headless,
            max_papers=max_papers,
            force=force
        )
        
        click.echo()
        result_msg = f"✅ Download complete: {success} success, {failure} failed"
        if skipped > 0:
            result_msg += f", {skipped} skipped (already downloaded)"
        click.echo(result_msg)
        if failure > 0:
            click.echo()
            click.echo("💡 Some videos may still be generating. Try again later.")
            
    except Exception as e:
        logger.exception("Video download failed")
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


# =============================================================================
# Digest Command
# =============================================================================

@main.command()
@click.option(
    "--week", "-w",
    default=None,
    help="Week ID (e.g., 2026-01). Defaults to current week."
)
@click.option(
    "--all", "-a",
    "include_all",
    is_flag=True,
    help="Include all papers, not just those with videos"
)
def digest(week: Optional[str], include_all: bool) -> None:
    """
    Generate weekly digest files.
    
    Creates Markdown and JSON files summarizing all processed
    papers for the specified week.
    """
    from .digest import generate_digest, print_digest_summary
    
    logger = get_logger()
    week_id = week or get_current_week_id()
    
    try:
        click.echo(f"📝 Generating digest for week {week_id}...")
        
        md_path, json_path = generate_digest(week_id, include_all=include_all)
        
        click.echo(f"✅ Digest generated:")
        click.echo(f"   Markdown: {md_path}")
        click.echo(f"   JSON: {json_path}")
        
        print_digest_summary(week_id)
        
    except Exception as e:
        logger.exception("Digest generation failed")
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


# =============================================================================
# Run Command (Full Pipeline)
# =============================================================================

@main.command()
@click.option(
    "--week", "-w",
    default=None,
    help="Week ID (e.g., 2026-01). Defaults to current week."
)
@click.option(
    "--max", "-m",
    "max_papers",
    default=10,
    type=int,
    help="Maximum papers to process (default: 10)"
)
@click.option(
    "--headful",
    is_flag=True,
    help="Run browser in visible mode (required for first-time login)"
)
@click.option(
    "--force", "-f",
    is_flag=True,
    help="Force reprocessing of already completed papers"
)
@click.option(
    "--skip-nblm",
    is_flag=True,
    help="Skip NotebookLM processing (fetch + download only)"
)
def run(
    week: Optional[str],
    max_papers: int,
    headful: bool,
    force: bool,
    skip_nblm: bool
) -> None:
    """
    Run the full pipeline: fetch → download → nblm → digest.
    
    This is the main command for processing a week's worth of papers
    through the entire workflow.
    """
    from .digest import generate_digest, print_digest_summary
    from .hf_fetcher import fetch_weekly_papers
    from .nblm_bot import process_papers_for_week
    from .pdf_downloader import download_pdfs_for_week
    
    logger = get_logger()
    week_id = week or get_current_week_id()
    headless = not headful
    
    click.echo(f"🚀 Running full pipeline for week {week_id}")
    click.echo(f"   Max papers: {max_papers}")
    click.echo(f"   Mode: {'Headful' if headful else 'Headless'}")
    click.echo()
    
    try:
        # Step 1: Fetch
        click.echo("=" * 50)
        click.echo("📚 Step 1: Fetching papers from Hugging Face...")
        papers = fetch_weekly_papers(week_id, max_papers=max_papers)
        click.echo(f"   Fetched {len(papers)} papers")
        
        if not papers:
            click.echo("⚠️  No papers found for this week.")
            return
        
        # Step 2: Download
        click.echo()
        click.echo("=" * 50)
        click.echo("📄 Step 2: Downloading PDFs from arXiv...")
        dl_success, dl_failure = download_pdfs_for_week(
            week_id, force=force, max_papers=max_papers
        )
        click.echo(f"   Downloads: {dl_success} success, {dl_failure} failed")
        
        # Step 3: NotebookLM (optional)
        if not skip_nblm:
            click.echo()
            click.echo("=" * 50)
            click.echo("🤖 Step 3: Processing through NotebookLM...")
            nblm_success, nblm_failure = process_papers_for_week(
                week_id=week_id,
                headless=headless,
                max_papers=max_papers,
                force=force
            )
            click.echo(f"   NotebookLM: {nblm_success} success, {nblm_failure} failed")
        else:
            click.echo()
            click.echo("=" * 50)
            click.echo("⏭️  Step 3: Skipping NotebookLM processing (--skip-nblm)")
        
        # Step 4: Digest
        click.echo()
        click.echo("=" * 50)
        click.echo("📝 Step 4: Generating digest...")
        md_path, json_path = generate_digest(week_id)
        click.echo(f"   Markdown: {md_path}")
        click.echo(f"   JSON: {json_path}")
        
        # Summary
        click.echo()
        click.echo("=" * 50)
        click.echo("🎉 Pipeline complete!")
        print_digest_summary(week_id)
        
    except KeyboardInterrupt:
        click.echo("\n⚠️  Pipeline interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.exception("Pipeline failed")
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


# =============================================================================
# Status Command
# =============================================================================

@main.command()
@click.option(
    "--week", "-w",
    default=None,
    help="Week ID (e.g., 2026-01). Defaults to current week."
)
@click.option(
    "--status", "-s",
    "filter_status",
    default=None,
    type=click.Choice(["NEW", "PDF_OK", "NBLM_OK", "VIDEO_OK", "ERROR"]),
    help="Filter by status"
)
@click.option(
    "--limit", "-l",
    default=20,
    type=int,
    help="Maximum papers to show (default: 20)"
)
@click.option(
    "--min-quality",
    type=float,
    default=0.0,
    help="Minimum quality score filter (0-100)"
)
@click.option(
    "--show-scores/--no-show-scores",
    default=False,
    help="Show quality scores in output"
)
def status(
    week: Optional[str],
    filter_status: Optional[str],
    limit: int,
    min_quality: float,
    show_scores: bool
) -> None:
    """
    Show status of papers in the database.

    Lists papers with their current processing status.
    """
    from .digest import print_digest_summary
    from .db import list_papers_by_quality

    week_id = week or get_current_week_id()

    # Get papers with quality filtering
    if min_quality > 0 or show_scores:
        papers = list_papers_by_quality(
            week_id=week_id,
            min_quality_score=min_quality,
            limit=limit
        )
        # Apply status filter if needed
        if filter_status:
            papers = [p for p in papers if p.status == filter_status]
    else:
        papers = list_papers(week_id=week_id, status=filter_status, limit=limit)

    if not papers:
        click.echo(f"No papers found for week {week_id}")
        if filter_status:
            click.echo(f"   (filtered by status: {filter_status})")
        if min_quality > 0:
            click.echo(f"   (filtered by quality >= {min_quality})")
        return

    # Print header
    click.echo(f"\n📋 Papers for week {week_id}")
    if filter_status:
        click.echo(f"   (filtered by status: {filter_status})")
    if min_quality > 0:
        click.echo(f"   (filtered by quality >= {min_quality})")
    click.echo()

    # Print table
    if show_scores:
        click.echo(f"{'Paper ID':<15} {'Score':<6} {'Status':<10} {'Title':<45}")
        click.echo("-" * 80)
    else:
        click.echo(f"{'Paper ID':<15} {'Status':<10} {'Title':<50}")
        click.echo("-" * 75)

    for paper in papers:
        title = (paper.title or "Untitled")[:42 if show_scores else 47]
        if len(paper.title or "") > (42 if show_scores else 47):
            title += "..."
        status_icon = {
            Status.NEW: "🆕",
            Status.PDF_OK: "📄",
            Status.NBLM_OK: "📓",
            Status.VIDEO_OK: "✅",
            Status.ERROR: "❌",
        }.get(paper.status, "❓")

        if show_scores:
            score_str = f"{paper.quality_score:.1f}" if paper.quality_score else "N/A"
            filtered_mark = "🚫" if paper.filtered_out else ""
            click.echo(f"{paper.paper_id:<15} {score_str:<6} {status_icon} {paper.status:<8} {title} {filtered_mark}")
        else:
            click.echo(f"{paper.paper_id:<15} {status_icon} {paper.status:<8} {title}")

    # Print summary
    print_digest_summary(week_id)


# =============================================================================
# Login Command
# =============================================================================

@main.command()
def login() -> None:
    """
    Open browser for Google login to NotebookLM.
    
    Use this command for first-time setup to authenticate
    with your Google account. The session will be saved
    for future headless runs.
    """
    from .nblm_bot import NotebookLMBot
    
    click.echo("🔐 Opening browser for Google login...")
    click.echo("   Please complete the login process in the browser window.")
    click.echo("   The session will be saved for future use.")
    click.echo()
    
    with NotebookLMBot(headless=False) as bot:
        if bot.navigate_to_notebooklm():
            click.echo("✅ Already logged in!")
        else:
            click.echo("⏳ Waiting for login...")
            if bot.wait_for_login(timeout=300):
                click.echo("✅ Login successful! Session saved.")
            else:
                click.echo("❌ Login timeout. Please try again.", err=True)
                sys.exit(1)


# =============================================================================
# Publish Command (Phase 3)
# =============================================================================

@main.command()
@click.option(
    "--week", "-w",
    default=None,
    help="Week ID (e.g., 2026-01). Defaults to current week."
)
@click.option(
    "--force", "-f",
    is_flag=True,
    help="Force re-upload even if already published"
)
@click.option(
    "--digest-only",
    is_flag=True,
    help="Only generate digest markdown, don't upload videos"
)
def publish(
    week: Optional[str],
    force: bool,
    digest_only: bool
) -> None:
    """
    Publish videos to HuggingFace and generate digest.
    
    Phase 3 of the workflow:
    1. Upload videos to HuggingFace Dataset
    2. Update metadata.json with video links
    3. Generate markdown digest with embedded video links
    
    Requires HF_TOKEN and HF_USERNAME in .env file.
    """
    from .publisher import (
        generate_digest_markdown,
        get_hf_dataset_id,
        publish_week,
    )
    
    logger = get_logger()
    week_id = week or get_current_week_id()
    
    try:
        dataset_id = get_hf_dataset_id()
        click.echo(f"🚀 Publishing videos for week {week_id}")
        click.echo(f"   Dataset: {dataset_id}")
        click.echo()
        
        if not digest_only:
            # Upload videos
            click.echo("=" * 50)
            click.echo("📤 Uploading videos to HuggingFace...")
            
            success, failure = publish_week(week_id, force=force)
            
            click.echo(f"   Uploaded: {success} success, {failure} failed")
            
            if success == 0 and failure == 0:
                click.echo("⚠️  No videos to publish. Run 'apd download-video' first.")
                return
        
        # Generate digest
        click.echo()
        click.echo("=" * 50)
        click.echo("📝 Generating digest markdown...")
        
        try:
            md_path = generate_digest_markdown(week_id)
            click.echo(f"   Generated: {md_path}")
        except ValueError as e:
            click.echo(f"⚠️  {e}")
            click.echo("   Digest generation skipped.")
            return
        
        # Summary
        click.echo()
        click.echo("=" * 50)
        click.echo("🎉 Publish complete!")
        click.echo()
        click.echo(f"   📺 Videos: https://huggingface.co/datasets/{dataset_id}")
        click.echo(f"   📄 Digest: {md_path}")
        
    except ValueError as e:
        click.echo(f"❌ Configuration error: {e}", err=True)
        click.echo("   Please check your .env file.", err=True)
        sys.exit(1)
    except Exception as e:
        logger.exception("Publish failed")
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


# =============================================================================
# Douyin Commands (Phase 4)
# =============================================================================

@main.command()
def douyin_login() -> None:
    """
    Open browser for manual login to Douyin Creator Studio.
    
    This will open a headful browser for you to scan the QR code.
    The session will be saved for future automated publishing.
    """
    from .douyin_bot import DouyinBot
    
    click.echo("🔐 Opening browser for Douyin login...")
    click.echo("   Please scan the QR code to log in to Creator Studio.")
    click.echo("   The session will be saved for future automated publishing.")
    click.echo()
    
    with DouyinBot(headless=False) as bot:
        if bot.login():
            click.echo("✅ Douyin login successful! Session saved.")
        else:
            click.echo("❌ Douyin login failed or timed out.", err=True)
            sys.exit(1)


@main.command()
@click.option(
    "--week", "-w",
    default=None,
    help="Week ID (e.g., 2026-01). Defaults to current week if no --date specified."
)
@click.option(
    "--date", "-d",
    default=None,
    help="Date (e.g., 2026-01-08). Publish videos for a specific date."
)
@click.option(
    "--paper-id", "-p",
    help="ArXiv ID of a specific paper to publish."
)
@click.option(
    "--force", "-f",
    is_flag=True,
    help="Force re-publish even if already marked as VIDEO_OK."
)
@click.option(
    "--headful",
    is_flag=True,
    help="Run in headful mode (visible browser)."
)
@click.option(
    "--auto-publish",
    is_flag=True,
    help="Automatically click publish button (default: manual publish)."
)
def publish_douyin(
    week: Optional[str],
    date: Optional[str],
    paper_id: Optional[str],
    force: bool,
    headful: bool,
    auto_publish: bool
) -> None:
    """
    Publish videos to Douyin Creator Studio.
    
    Use --week for weekly papers or --date for a specific date.
    
    Phase 4 of the workflow:
    1. Authenticate using saved session
    2. Upload video file
    3. Fill in title, description, and tags
    4. Click Publish
    """
    from .douyin_bot import DouyinBot
    from .db import get_paper, list_papers
    
    logger = get_logger()
    
    # Validate mutually exclusive options
    if week and date:
        click.echo("❌ Error: --week and --date are mutually exclusive. Use one or the other.", err=True)
        sys.exit(1)
    
    # Determine period_id (date or week)
    if date:
        period_id = date
        period_type = "date"
    else:
        period_id = week or get_current_week_id()
        period_type = "week"
    
    # Identify papers to publish
    if paper_id:
        papers = [get_paper(paper_id)]
        if not papers[0]:
            click.echo(f"❌ Paper {paper_id} not found in database.", err=True)
            sys.exit(1)
    else:
        # Publish all papers for the period that have videos
        papers = list_papers(week_id=period_id, status=Status.VIDEO_OK)
        
    if not papers:
        click.echo(f"⚠️  No papers with videos found for {period_type} {period_id}.")
        click.echo("   Run 'apd download-video' first.")
        return
        
    click.echo(f"🚀 Publishing {len(papers)} videos to Douyin...")
    
    with DouyinBot(headless=not headful) as bot:
        # Check login first (only once at the beginning)
        if not bot.is_logged_in():
            click.echo("❌ Not logged into Douyin. Please run 'apd douyin-login' first.", err=True)
            sys.exit(1)
            
        success_count = 0
        total_papers = len(papers)
        
        for idx, paper in enumerate(papers, 1):
            click.echo(f"\n{'='*50}")
            click.echo(f"📹 Processing video {idx}/{total_papers}")
            
            if not paper.video_path:
                click.echo(f"⏭️  Skipping {paper.paper_id}: No video path found.")
                continue
                
            video_path = Path(paper.video_path)
            if not video_path.exists():
                click.echo(f"❌ Skipping {paper.paper_id}: Video file not found at {video_path}")
                continue
                
            click.echo(f"📤 Uploading {paper.paper_id}: {paper.title}")
            
            # Construct description - use summary if available, otherwise fallback to template
            if paper.summary:
                description = f"{paper.summary}\n\narXiv: {paper.paper_id}"
            else:
                description = f"arXiv: {paper.paper_id}\n{paper.title}\n\nAutomated digest generated by Auto-Paper-Digest."
            tags = ["AI", "Research", "Arxiv", "MachineLearning"]
            
            # Skip login check since we already verified at the start
            if bot.publish_video(
                video_path=video_path,
                title=paper.title[:30],  # Douyin title limit is 30 chars
                description=description,
                tags=tags,
                skip_login_check=True,  # Skip login check for batch publishing
                auto_publish=auto_publish  # Use the --auto-publish flag
            ):
                click.echo(f"✅ Successfully published {paper.paper_id}!")
                success_count += 1
            else:
                click.echo(f"❌ Failed to publish {paper.paper_id}.")
                
        click.echo()
        click.echo(f"🎉 Douyin publish complete: {success_count}/{total_papers} successful.")


# =============================================================================
# 新增命令：新闻获取
# =============================================================================

@main.command("fetch-news")
@click.option(
    "--week", "-w",
    default=None,
    help="Week ID (e.g., 2026-01)."
)
@click.option(
    "--date", "-d",
    default=None,
    help="Date (YYYY-MM-DD), e.g., 2026-01-20. Fetches hot news for that date."
)
@click.option(
    "--max", "-m",
    "max_news",
    default=50,
    type=int,
    help="Maximum news to fetch (default: 50)"
)
@click.option(
    "--source", "-s",
    default="weibo",
    type=click.Choice(["weibo", "zhihu", "baidu"]),
    help="News source (default: weibo)"
)
def fetch_news(week: Optional[str], date: Optional[str], max_news: int, source: str) -> None:
    """
    Fetch hot news from Chinese news sources.

    Supports: weibo (微博热搜), zhihu (知乎热榜), baidu (百度热搜)

    Examples:
        apd fetch-news --date 2026-01-20 --source weibo
        apd fetch-news --week 2026-03 --source zhihu --max 20
    """
    from .news_fetcher import fetch_daily_news, fetch_weekly_news

    logger = get_logger()

    # Validate mutually exclusive options
    if week and date:
        click.echo("❌ Error: --week and --date are mutually exclusive.", err=True)
        sys.exit(1)

    try:
        if date:
            # Date-based fetching
            click.echo(f"📰 Fetching hot news for date {date} from {source}...")
            news_list = fetch_daily_news(date, max_news=max_news, source=source)
            click.echo(f"✅ Fetched {len(news_list)} news items")

            # Show stats
            total = count_papers(week_id=date)
            click.echo(f"   Total items in database for {date}: {total}")
        else:
            # Week-based fetching (default)
            week_id = week or get_current_week_id()
            click.echo(f"📰 Fetching hot news for week {week_id} from {source}...")
            news_list = fetch_weekly_news(week_id, max_news=max_news, source=source)
            click.echo(f"✅ Fetched {len(news_list)} news items")

            # Show stats
            total = count_papers(week_id=week_id)
            click.echo(f"   Total items in database for {week_id}: {total}")

    except Exception as e:
        logger.exception("News fetch failed")
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


# =============================================================================
# 新增命令：GitHub Trending 获取
# =============================================================================

@main.command("fetch-github")
@click.option(
    "--week", "-w",
    default=None,
    help="Week ID (e.g., 2026-01)."
)
@click.option(
    "--date", "-d",
    default=None,
    help="Date (YYYY-MM-DD), e.g., 2026-01-20."
)
@click.option(
    "--max", "-m",
    "max_projects",
    default=25,
    type=int,
    help="Maximum projects to fetch (default: 25)"
)
@click.option(
    "--language", "-l",
    default=None,
    help="Filter by programming language (e.g., python, javascript)"
)
@click.option(
    "--since",
    default="daily",
    type=click.Choice(["daily", "weekly", "monthly"]),
    help="Time range (default: daily)"
)
def fetch_github(
    week: Optional[str],
    date: Optional[str],
    max_projects: int,
    language: Optional[str],
    since: str
) -> None:
    """
    Fetch GitHub Trending repositories.

    Examples:
        apd fetch-github --date 2026-01-20 --max 20
        apd fetch-github --week 2026-03 --language python --since weekly
    """
    from .github_fetcher import fetch_daily_github_trending, fetch_weekly_github_trending

    logger = get_logger()

    # Validate mutually exclusive options
    if week and date:
        click.echo("❌ Error: --week and --date are mutually exclusive.", err=True)
        sys.exit(1)

    try:
        if date:
            # Date-based fetching
            click.echo(f"🔥 Fetching GitHub Trending for date {date}...")
            if language:
                click.echo(f"   Language filter: {language}")
            projects = fetch_daily_github_trending(date, max_projects=max_projects, language=language, since=since)
            click.echo(f"✅ Fetched {len(projects)} GitHub projects")

            # Show stats
            total = count_papers(week_id=date)
            click.echo(f"   Total items in database for {date}: {total}")
        else:
            # Week-based fetching (default)
            week_id = week or get_current_week_id()
            click.echo(f"🔥 Fetching GitHub Trending for week {week_id}...")
            if language:
                click.echo(f"   Language filter: {language}")
            projects = fetch_weekly_github_trending(week_id, max_projects=max_projects, language=language)
            click.echo(f"✅ Fetched {len(projects)} GitHub projects")

            # Show stats
            total = count_papers(week_id=week_id)
            click.echo(f"   Total items in database for {week_id}: {total}")

    except Exception as e:
        logger.exception("GitHub fetch failed")
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


# =============================================================================
# 新增命令：B站登录
# =============================================================================

@main.command("bilibili-login")
def bilibili_login() -> None:
    """
    Open browser for Bilibili Creator login.

    This will open a headful browser for you to scan the QR code.
    The session will be saved for future automated publishing.
    """
    from .bilibili_bot import BilibiliBot

    click.echo("🔐 Opening browser for Bilibili login...")
    click.echo("   Please scan the QR code to log in to Creator Studio.")
    click.echo("   The session will be saved for future use.")
    click.echo()

    with BilibiliBot(headless=False) as bot:
        if bot.login():
            click.echo("✅ Bilibili login successful! Session saved.")
        else:
            click.echo("❌ Bilibili login failed or timed out.", err=True)
            sys.exit(1)


# =============================================================================
# 新增命令：B站发布
# =============================================================================

@main.command("publish-bilibili")
@click.option(
    "--week", "-w",
    default=None,
    help="Week ID (e.g., 2026-01). Defaults to current week if no --date specified."
)
@click.option(
    "--date", "-d",
    default=None,
    help="Date (e.g., 2026-01-20). Publish videos for a specific date."
)
@click.option(
    "--paper-id", "-p",
    help="Content ID of a specific item to publish."
)
@click.option(
    "--force", "-f",
    is_flag=True,
    help="Force re-publish even if already published."
)
@click.option(
    "--headful",
    is_flag=True,
    help="Run in headful mode (visible browser, required for manual publish)."
)
@click.option(
    "--auto-publish",
    is_flag=True,
    help="Automatically click publish button (default: manual publish)."
)
def publish_bilibili(
    week: Optional[str],
    date: Optional[str],
    paper_id: Optional[str],
    force: bool,
    headful: bool,
    auto_publish: bool
) -> None:
    """
    Publish videos to Bilibili Creator Studio (semi-automatic mode by default).

    By default, the script will upload the video and fill in all information,
    then pause for you to manually click the publish button.

    Use --auto-publish to automatically click publish (not recommended).

    Examples:
        apd publish-bilibili --date 2026-01-20 --headful
        apd publish-bilibili --week 2026-03 --headful --auto-publish
    """
    from .bilibili_bot import BilibiliBot
    from .db import get_paper, list_papers

    logger = get_logger()

    # Validate mutually exclusive options
    if week and date:
        click.echo("❌ Error: --week and --date are mutually exclusive.", err=True)
        sys.exit(1)

    # Determine period_id (date or week)
    if date:
        period_id = date
        period_type = "date"
    else:
        period_id = week or get_current_week_id()
        period_type = "week"

    # Identify items to publish
    if paper_id:
        papers = [get_paper(paper_id)]
        if not papers[0]:
            click.echo(f"❌ Item {paper_id} not found in database.", err=True)
            sys.exit(1)
    else:
        # Publish all items for the period that have videos
        papers = list_papers(week_id=period_id, status=Status.VIDEO_OK)

    if not papers:
        click.echo(f"⚠️  No items with videos found for {period_type} {period_id}.")
        click.echo("   Run 'apd download-video' first.")
        return

    click.echo(f"🚀 Publishing {len(papers)} videos to Bilibili...")
    if not auto_publish:
        click.echo("📌 Semi-automatic mode: You will manually click publish button")

    with BilibiliBot(headless=not headful) as bot:
        # Check login first
        if not bot.is_logged_in():
            click.echo("❌ Not logged into Bilibili. Please run 'apd bilibili-login' first.", err=True)
            sys.exit(1)

        success_count = 0
        total_papers = len(papers)

        for idx, paper in enumerate(papers, 1):
            click.echo(f"\n{'='*50}")
            click.echo(f"📹 Processing video {idx}/{total_papers}")

            if not paper.video_path:
                click.echo(f"⏭️  Skipping {paper.paper_id}: No video path found.")
                continue

            video_path = Path(paper.video_path)
            if not video_path.exists():
                click.echo(f"❌ Skipping {paper.paper_id}: Video file not found at {video_path}")
                continue

            click.echo(f"📤 Uploading {paper.paper_id}: {paper.title}")

            # Construct description
            if paper.summary:
                description = f"{paper.summary}\n\n"
            else:
                description = ""

            # Add source info based on content type
            if paper.content_type == "GITHUB":
                description += f"GitHub: {paper.source_url}\n"
                description += f"⭐ Stars: {paper.github_stars}\n"
                if paper.github_language:
                    description += f"Language: {paper.github_language}\n"
            elif paper.content_type == "NEWS":
                description += f"来源: {paper.news_source}\n"
                description += f"原文: {paper.news_url}\n"
            else:  # PAPER
                description += f"arXiv: {paper.paper_id}\n"

            description += "\nAutomated by Auto-Paper-Digest"

            # Tags based on content type
            if paper.content_type == "GITHUB":
                tags = ["GitHub", "开源项目", "编程"]
                if paper.github_language:
                    tags.append(paper.github_language)
            elif paper.content_type == "NEWS":
                tags = ["热点", "新闻", paper.news_source or "资讯"]
            else:  # PAPER
                tags = ["AI", "论文", "Research", "MachineLearning"]

            # Publish video
            if bot.publish_video(
                video_path=video_path,
                title=paper.title[:80],  # B站标题限制80字符
                description=description,
                tags=tags,
                skip_login_check=True,
                auto_publish=auto_publish
            ):
                click.echo(f"✅ Successfully processed {paper.paper_id}!")
                success_count += 1
            else:
                click.echo(f"❌ Failed to process {paper.paper_id}.")

        click.echo()
        click.echo(f"🎉 Bilibili publish complete: {success_count}/{total_papers} successful.")


# =============================================================================
# 新增命令：小红书登录
# =============================================================================

@main.command("xiaohongshu-login")
def xiaohongshu_login() -> None:
    """
    Open browser for Xiaohongshu Creator login.

    This will open a headful browser for you to scan the QR code.
    The session will be saved for future automated publishing.
    """
    from .xiaohongshu_bot import XiaohongshuBot

    click.echo("🔐 Opening browser for Xiaohongshu login...")
    click.echo("   Please scan the QR code to log in to Creator Center.")
    click.echo("   The session will be saved for future use.")
    click.echo()

    with XiaohongshuBot(headless=False) as bot:
        if bot.login():
            click.echo("✅ Xiaohongshu login successful! Session saved.")
        else:
            click.echo("❌ Xiaohongshu login failed or timed out.", err=True)
            sys.exit(1)


# =============================================================================
# 新增命令：小红书发布
# =============================================================================

@main.command("publish-xiaohongshu")
@click.option(
    "--week", "-w",
    default=None,
    help="Week ID (e.g., 2026-01). Defaults to current week if no --date specified."
)
@click.option(
    "--date", "-d",
    default=None,
    help="Date (e.g., 2026-01-20). Publish videos for a specific date."
)
@click.option(
    "--paper-id", "-p",
    help="Content ID of a specific item to publish."
)
@click.option(
    "--force", "-f",
    is_flag=True,
    help="Force re-publish even if already published."
)
@click.option(
    "--headful",
    is_flag=True,
    help="Run in headful mode (visible browser, required for manual publish)."
)
@click.option(
    "--auto-publish",
    is_flag=True,
    help="Automatically click publish button (default: manual publish)."
)
def publish_xiaohongshu(
    week: Optional[str],
    date: Optional[str],
    paper_id: Optional[str],
    force: bool,
    headful: bool,
    auto_publish: bool
) -> None:
    """
    Publish videos to Xiaohongshu (Little Red Book) Creator Center.

    By default, uses semi-automatic mode: uploads video and fills in information,
    then pauses for you to manually click the publish button.

    Use --auto-publish to automatically click publish (not recommended).

    Examples:
        apd publish-xiaohongshu --date 2026-01-20 --headful
        apd publish-xiaohongshu --week 2026-03 --headful --auto-publish
    """
    from .xiaohongshu_bot import XiaohongshuBot
    from .db import get_paper, list_papers, update_paper
    from .config import DEFAULT_TAGS

    logger = get_logger()

    # Validate mutually exclusive options
    if week and date:
        click.echo("❌ Error: --week and --date are mutually exclusive.", err=True)
        sys.exit(1)

    # Determine period_id (date or week)
    if date:
        period_id = date
        period_type = "date"
    else:
        period_id = week or get_current_week_id()
        period_type = "week"

    # Identify items to publish
    if paper_id:
        papers = [get_paper(paper_id)]
        if not papers[0]:
            click.echo(f"❌ Item {paper_id} not found in database.", err=True)
            sys.exit(1)
    else:
        # Publish all items for the period that have videos
        papers = list_papers(week_id=period_id, status=Status.VIDEO_OK)

    if not papers:
        click.echo(f"⚠️  No items with videos found for {period_type} {period_id}.")
        click.echo("   Run 'apd download-video' first.")
        return

    # Filter out already published (unless --force)
    if not force:
        papers = [p for p in papers if not p.xiaohongshu_published]
        if not papers:
            click.echo(f"✅ All videos for {period_type} {period_id} already published to Xiaohongshu.")
            click.echo("   Use --force to re-publish.")
            return

    click.echo(f"🚀 Publishing {len(papers)} videos to Xiaohongshu...")
    if not auto_publish:
        click.echo("📌 Semi-automatic mode: You will manually click publish button")
    click.echo()

    with XiaohongshuBot(headless=not headful) as bot:
        # Check login first
        if not bot._is_logged_in():
            click.echo("❌ Not logged into Xiaohongshu. Please run 'apd xiaohongshu-login' first.", err=True)
            sys.exit(1)

        success_count = 0
        total_papers = len(papers)

        for idx, paper in enumerate(papers, 1):
            click.echo(f"\n{'='*60}")
            click.echo(f"📹 Processing video {idx}/{total_papers}")

            if not paper.video_path:
                click.echo(f"⏭️  Skipping {paper.paper_id}: No video path found.")
                continue

            video_path = Path(paper.video_path)
            if not video_path.exists():
                click.echo(f"❌ Skipping {paper.paper_id}: Video file not found at {video_path}")
                continue

            click.echo(f"📤 Uploading {paper.paper_id}: {paper.title}")

            # Construct description
            if paper.summary:
                description = f"{paper.summary}\n\n"
            else:
                description = ""

            # Add source info based on content type
            if paper.content_type == "GITHUB":
                description += f"GitHub: {paper.source_url}\n"
                description += f"⭐ Stars: {paper.github_stars}\n"
                if paper.github_language:
                    description += f"Language: {paper.github_language}\n"
            elif paper.content_type == "NEWS":
                description += f"来源: {paper.news_source}\n"
                description += f"原文: {paper.news_url}\n"
            else:  # PAPER
                description += f"📚 arXiv: {paper.paper_id}\n"
                if paper.pdf_url:
                    description += f"PDF: {paper.pdf_url}\n"

            description += "\n🤖 由 Auto-Paper-Digest 自动生成"

            # Tags based on content type
            if paper.content_type == "GITHUB":
                tags = DEFAULT_TAGS.get("github", ["GitHub", "开源项目", "编程"])
                if paper.github_language:
                    tags = tags[:3] + [paper.github_language]
            elif paper.content_type == "NEWS":
                tags = DEFAULT_TAGS.get("news", ["热点", "新闻", "资讯"])
            else:  # PAPER
                tags = DEFAULT_TAGS.get("paper", ["AI", "论文解读", "学术", "科技"])

            # Publish video
            try:
                result = bot.publish_video(
                    video_path=video_path,
                    title=paper.title[:100],  # 小红书标题限制100字符
                    description=description[:1000],  # 小红书描述限制1000字符
                    tags=tags[:5],  # 最多5个标签
                    auto_publish=auto_publish
                )

                if result.get('success'):
                    click.echo(f"✅ Successfully published {paper.paper_id}!")

                    # Update database
                    update_paper(
                        paper_id=paper.paper_id,
                        xiaohongshu_published=1,
                        xiaohongshu_note_id=result.get('note_id'),
                        xiaohongshu_url=result.get('url')
                    )
                    success_count += 1
                else:
                    click.echo(f"❌ Failed to publish {paper.paper_id}: {result.get('error', 'Unknown error')}")

            except Exception as e:
                click.echo(f"❌ Error publishing {paper.paper_id}: {e}")
                logger.error(f"Xiaohongshu publish error: {e}", exc_info=True)

        click.echo()
        click.echo(f"🎉 Xiaohongshu publish complete: {success_count}/{total_papers} successful.")


# =============================================================================
# Deduplication Commands
# =============================================================================

@main.command()
@click.option(
    "--week", "-w",
    default=None,
    help="Week ID (e.g., 2026-05). Defaults to current week."
)
@click.option(
    "--date", "-d",
    default=None,
    help="Date (e.g., 2026-02-03). Check papers for a specific date."
)
@click.option(
    "--show-details",
    is_flag=True,
    help="Show detailed similarity scores"
)
@click.option(
    "--auto-merge",
    is_flag=True,
    help="Automatically merge duplicates (use with caution)"
)
@click.option(
    "--use-semantic/--no-semantic",
    default=True,
    help="Use semantic similarity (slower but more accurate)"
)
def dedup(
    week: Optional[str],
    date: Optional[str],
    show_details: bool,
    auto_merge: bool,
    use_semantic: bool
) -> None:
    """
    Detect and handle duplicate content.

    Checks for duplicate papers using multiple similarity methods:
    - URL matching (arXiv IDs)
    - Title similarity
    - Semantic similarity (optional)
    """
    from .deduplicator import Deduplicator
    from .db import save_duplicate_group, mark_as_duplicate

    logger = get_logger()

    # Determine week_id
    if date and week:
        click.echo("❌ Error: --week and --date are mutually exclusive.", err=True)
        sys.exit(1)

    week_id = date or week or get_current_week_id()

    click.echo(f"🔍 Checking for duplicates in {week_id}...")
    if not use_semantic:
        click.echo("   (Semantic similarity disabled for faster processing)")

    # Get papers
    papers = list_papers(week_id=week_id)

    if not papers:
        click.echo(f"No papers found for {week_id}")
        return

    click.echo(f"   Found {len(papers)} papers to check")

    # Convert to dict format
    papers_data = []
    for paper in papers:
        papers_data.append({
            'paper_id': paper.paper_id,
            'title': paper.title or '',
            'pdf_url': paper.pdf_url or '',
            'hf_url': paper.hf_url or '',
            'abstract': paper.summary or '',  # Use summary as abstract
        })

    # Run deduplication
    deduplicator = Deduplicator()
    result = deduplicator.find_duplicates(papers_data, use_semantic=use_semantic)

    # Display results
    if not result.duplicate_groups:
        click.echo("\n✅ No duplicates found!")
        return

    click.echo(f"\n📊 Deduplication Results:")
    click.echo(f"   Total papers: {result.total_papers}")
    click.echo(f"   Unique papers: {result.unique_papers}")
    click.echo(f"   Duplicate groups: {len(result.duplicate_groups)}")
    click.echo(f"   Duplicates removed: {result.duplicates_removed}")
    click.echo(f"   Deduplication rate: {result.duplicates_removed/result.total_papers*100:.1f}%")

    stats = deduplicator.get_deduplication_stats(result)
    click.echo(f"\n📈 Detection Methods:")
    click.echo(f"   Exact URL: {stats['detection_methods']['exact_url']}")
    click.echo(f"   Title similarity: {stats['detection_methods']['title_similarity']}")
    click.echo(f"   Semantic similarity: {stats['detection_methods']['semantic_similarity']}")

    # Show details
    if show_details:
        click.echo(f"\n📋 Duplicate Groups:\n")
        for i, group in enumerate(result.duplicate_groups, 1):
            click.echo(f"Group {i}: {group.detection_method}")
            click.echo(f"  Primary: {group.canonical_paper_id}")
            click.echo(f"  Duplicates:")
            for dup_id in group.duplicate_paper_ids:
                score = group.similarity_scores.get(dup_id, 0.0)
                click.echo(f"    - {dup_id} (similarity: {score:.2f})")
            click.echo()

    # Save to database
    click.echo("💾 Saving duplicate groups to database...")
    for group in result.duplicate_groups:
        save_duplicate_group(
            group_id=group.group_id,
            canonical_paper_id=group.canonical_paper_id,
            duplicate_paper_ids=group.duplicate_paper_ids,
            similarity_scores=group.similarity_scores,
            detection_method=group.detection_method,
            created_at=group.created_at
        )

    # Auto-merge if requested
    if auto_merge:
        click.echo("\n⚠️  Auto-merging duplicates...")
        if not click.confirm("This will mark duplicates in the database. Continue?"):
            click.echo("Cancelled.")
            return

        merged_count = 0
        for group in result.duplicate_groups:
            for dup_id in group.duplicate_paper_ids:
                mark_as_duplicate(dup_id, group.canonical_paper_id)
                merged_count += 1

        click.echo(f"✅ Marked {merged_count} papers as duplicates")
    else:
        click.echo("\n💡 Tip: Use --auto-merge to automatically mark duplicates")


@main.command()
@click.option(
    "--status",
    type=click.Choice(["pending", "merged", "ignored"]),
    default=None,
    help="Filter by merge status"
)
@click.option(
    "--limit", "-l",
    default=20,
    type=int,
    help="Maximum groups to show"
)
def dedup_groups(status: Optional[str], limit: int) -> None:
    """
    Show duplicate groups.

    Lists all detected duplicate groups with their status.
    """
    from .db import get_duplicate_groups

    click.echo(f"📋 Duplicate Groups\n")

    groups = get_duplicate_groups(status=status, limit=limit)

    if not groups:
        click.echo("No duplicate groups found.")
        if status:
            click.echo(f"   (filtered by status: {status})")
        return

    for i, group in enumerate(groups, 1):
        click.echo(f"Group {i}: {group['group_id']}")
        click.echo(f"  Detection: {group['detection_method']}")
        click.echo(f"  Status: {group.get('merge_status', 'pending')}")
        click.echo(f"  Primary: {group['canonical_paper_id']}")
        click.echo(f"  Duplicates ({len(group['duplicate_paper_ids'])}):")
        for dup_id in group['duplicate_paper_ids'][:3]:  # Show first 3
            click.echo(f"    - {dup_id}")
        if len(group['duplicate_paper_ids']) > 3:
            click.echo(f"    ... and {len(group['duplicate_paper_ids']) - 3} more")
        click.echo()

    click.echo(f"Showing {len(groups)} groups")
    if status:
        click.echo(f"   (filtered by status: {status})")


# =============================================================================
# Recommendation Commands
# =============================================================================

@main.command()
@click.option("--week", "-w", default=None, help="Week ID (YYYY-WNN or YYYY-MM-DD)")
@click.option("--strategy", "-s",
              type=click.Choice(["popular", "similar", "collaborative", "hybrid"]),
              default="hybrid",
              help="Recommendation strategy")
@click.option("--limit", "-n", default=10, help="Number of recommendations")
@click.option("--user", "-u", default="default", help="User ID")
@click.option("--based-on", help="Paper ID for similar recommendations")
def recommend(
    week: Optional[str],
    strategy: str,
    limit: int,
    user: str,
    based_on: Optional[str]
) -> None:
    """Get personalized paper recommendations."""

    from .recommender import Recommender

    click.echo(f"🎯 Getting recommendations using {strategy} strategy...")

    recommender = Recommender(user_id=user)

    try:
        if strategy == "popular":
            results = recommender.recommend_popular(week_id=week, limit=limit)
        elif strategy == "similar":
            if not based_on:
                click.echo("❌ Error: --based-on required for similar strategy")
                return
            results = recommender.recommend_similar(paper_id=based_on, limit=limit)
        elif strategy == "collaborative":
            results = recommender.recommend_collaborative(limit=limit)
        elif strategy == "hybrid":
            results = recommender.recommend_hybrid(week_id=week, limit=limit)
        else:
            click.echo(f"❌ Unknown strategy: {strategy}")
            return
    except Exception as e:
        click.echo(f"❌ Error: {e}")
        logger.error(f"Recommendation failed: {e}", exc_info=True)
        return

    if not results:
        click.echo("📭 No recommendations found")
        return

    click.echo(f"\n✨ Found {len(results)} recommendations:\n")
    click.echo(f"{'#':<3} {'Score':<6} {'Strategy':<15} {'Title':<50}")
    click.echo("-" * 80)

    for i, result in enumerate(results, 1):
        score_str = f"{result.score:.2f}"
        title = result.title[:47] + "..." if len(result.title) > 50 else result.title
        click.echo(f"{i:<3} {score_str:<6} {result.strategy:<15} {title}")

        if result.reasons:
            reasons_str = " | ".join(result.reasons)
            click.echo(f"    💡 {reasons_str}")

        # 保存推荐记录
        try:
            recommender.save_recommendation(result)
        except Exception as e:
            logger.warning(f"Failed to save recommendation: {e}")


@main.command()
@click.argument("paper_id")
@click.option("--action", "-a",
              type=click.Choice(["view", "favorite", "share"]),
              required=True,
              help="Interaction type")
@click.option("--user", "-u", default="default", help="User ID")
def interact(paper_id: str, action: str, user: str) -> None:
    """Record user interaction with a paper."""

    from .recommender import Recommender

    recommender = Recommender(user_id=user)

    try:
        recommender.track_interaction(paper_id, action)
        click.echo(f"✅ Recorded {action} for paper {paper_id}")
    except Exception as e:
        click.echo(f"❌ Error: {e}")
        logger.error(f"Failed to track interaction: {e}", exc_info=True)


if __name__ == "__main__":
    main()


