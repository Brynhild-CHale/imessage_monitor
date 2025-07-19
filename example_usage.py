"""Real-time iMessage monitoring example."""
import asyncio
import signal
import sys
from pathlib import Path
from imessage_monitor import iMessageMonitor
from imessage_monitor.display import pretty_print_bubble, pretty_print_reaction, pretty_print_sticker


class RealTimeMonitor:
    """Real-time iMessage monitor with graceful shutdown."""
    
    def __init__(self, enable_ascii_art: bool = False):
        # Check if config.toml exists in current directory
        config_path = Path("config.toml")
        if config_path.exists():
            print(f"📋 Using config file: {config_path.absolute()}")
            self.monitor = iMessageMonitor(str(config_path))
        else:
            print("📋 No config.toml found, using default configuration")
            self.monitor = iMessageMonitor()
        
        self.enable_ascii_art = enable_ascii_art
        self.running = False
        self.message_count = 0
        
    def handle_new_message(self, message):
        """Handle incoming messages with pretty printing."""
        self.message_count += 1
        
        print(f"\n{'='*80}")
        print(f"📱 NEW MESSAGE #{self.message_count}")
        print(f"{'='*80}")
        
        # Determine message type and use appropriate pretty print
        associated_type = message.get('associated_message_type', 0)
        balloon_bundle_id = message.get('balloon_bundle_id', '')
        attachments = message.get('parsed_attachments', [])
        
        # Check if it's a sticker
        is_sticker = any(attachment.get('is_sticker', False) for attachment in attachments)
        
        if associated_type in range(2000, 4000):  # Reaction
            print("🔄 REACTION:")
            print(pretty_print_reaction(message))
        elif is_sticker:
            print("🎭 STICKER:")
            print(pretty_print_sticker(message, show_ascii_art=self.enable_ascii_art))
        else:
            print("💬 MESSAGE:")
            print(pretty_print_bubble(message, show_ascii_art=self.enable_ascii_art))
        
        # Show additional info
        sender = "You" if message.get('is_from_me') else message.get('handle_id_str', 'Unknown')
        service = message.get('service', 'Unknown')
        print(f"\n📊 From: {sender} | Service: {service}")
        
        if attachments:
            print(f"📎 Attachments: {len(attachments)}")
            for i, attachment in enumerate(attachments[:3]):  # Show first 3
                filename = attachment.get('filename', 'Unknown')
                size = attachment.get('size', 0)
                if size:
                    size_mb = size / (1024 * 1024)
                    print(f"   {i+1}. {filename} ({size_mb:.1f}MB)")
                else:
                    print(f"   {i+1}. {filename}")
    
    def setup_signal_handlers(self):
        """Setup graceful shutdown on Ctrl+C."""
        def signal_handler(signum, frame):
            print(f"\n\n⚠️  Received signal {signum}. Shutting down gracefully...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def start_monitoring(self):
        """Start real-time monitoring."""
        self.setup_signal_handlers()
        self.running = True
        
        print("🚀 Starting iMessage Real-Time Monitor")
        print("=" * 60)
        print(f"ASCII Art: {'Enabled' if self.enable_ascii_art else 'Disabled'}")
        print("=" * 60)
        
        try:
            # Start monitoring without showing initial messages
            print("📱 Initializing monitor...")
            initial_messages = self.monitor.start(message_callback=self.handle_new_message)
            print("✅ Monitor initialized")
            
            print("\n🎯 MONITORING ACTIVE - Waiting for new messages...")
            print("📞 Send yourself a message to test!")
            print("🛑 Press Ctrl+C to stop monitoring")
            print("=" * 60)
            
            # Keep the monitor running
            while self.running and self.monitor.is_running():
                await asyncio.sleep(0.5)  # Check every 0.5 seconds
                
        except KeyboardInterrupt:
            print("\n⚠️  Keyboard interrupt received")
        except Exception as e:
            print(f"\n❌ Error during monitoring: {e}")
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Clean shutdown of the monitor."""
        print("\n🛑 Stopping monitor...")
        
        if self.monitor.is_running():
            self.monitor.stop()
            
        print(f"📊 Session Summary:")
        print(f"   • Messages processed: {self.message_count}")
        print(f"   • Monitor status: {'Stopped' if not self.monitor.is_running() else 'Running'}")
        print("✅ Monitor stopped successfully")


def show_help():
    """Show usage instructions."""
    print("iMessage Real-Time Monitor")
    print("=" * 40)
    print("Usage:")
    print("  python example_usage.py [--ascii-art]")
    print("")
    print("Options:")
    print("  --ascii-art    Enable ASCII art for images (default: disabled)")
    print("  --help         Show this help message")
    print("")
    print("Controls:")
    print("  Ctrl+C         Stop monitoring")
    print("")
    print("Features:")
    print("  • Real-time message monitoring")
    print("  • Pretty-printed chat bubbles") 
    print("  • Reaction and sticker support")
    print("  • Attachment information")
    print("  • Graceful shutdown")


async def main():
    """Main entry point for real-time monitoring."""
    
    # Parse command line arguments
    enable_ascii_art = '--ascii-art' in sys.argv
    show_help_flag = '--help' in sys.argv or '-h' in sys.argv
    
    if show_help_flag:
        show_help()
        return
    
    # Create and start the monitor
    monitor = RealTimeMonitor(enable_ascii_art=enable_ascii_art)
    await monitor.start_monitoring()


if __name__ == "__main__":
    print("iMessage Monitor - Real-Time Monitoring")
    print("=" * 60)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)