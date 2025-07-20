"""Streamlined iMessage Monitor examples."""

import asyncio
from imessage_monitor import iMessageMonitor
from imessage_monitor.config import Config, ContactFilter, DateRange
from imessage_monitor.display import pretty_print_bubble


def simple_message_callback(message):
    """Simple message handler."""
    sender = "You" if message.get('is_from_me') else message.get('handle_id_str', 'Unknown')
    content = message.get('message_text') or '[Media/Reaction]'
    print(f"📱 {sender}: {content}")


def pretty_message_callback(message):
    """Pretty message handler using chat bubbles."""
    print(pretty_print_bubble(message))


async def example_real_time_monitoring():
    """Example: Basic real-time monitoring."""
    print("🚀 Real-time monitoring example")
    
    monitor = iMessageMonitor()
    monitor.start(message_callback=pretty_message_callback)
    
    print("Monitoring for 30 seconds...")
    await asyncio.sleep(30)
    monitor.stop()
    print("✅ Stopped\n")


def example_recent_messages():
    """Example: Get recent messages with time filters."""
    print("📋 Recent messages examples")
    
    # Example 1: Last hour of messages
    config = Config.default()
    config.date_range = DateRange.from_hours_back(1)
    
    monitor = iMessageMonitor()
    monitor.config = config
    messages = monitor.get_recent_messages(limit=10)
    
    print(f"Last hour: {len(messages)} messages")
    for msg in messages[:3]:
        sender = "You" if msg.get('is_from_me') else msg.get('handle_id_str', 'Unknown')
        content = msg.get('message_text') or '[Media]'
        print(f"  • {sender}: {content[:50]}...")
    
    # Example 2: Specific date range (3-4 hours ago)
    from datetime import datetime, timedelta
    end_time = datetime.now() - timedelta(hours=3)
    start_time = end_time - timedelta(hours=1)
    config.date_range = DateRange(start_date=start_time, end_date=end_time)
    monitor.config = config
    messages = monitor.get_recent_messages(limit=10)
    
    print(f"3-4 hours ago: {len(messages)} messages")
    for msg in messages[:3]:
        sender = "You" if msg.get('is_from_me') else msg.get('handle_id_str', 'Unknown')
        content = msg.get('message_text') or '[Media]'
        print(f"  • {sender}: {content[:50]}...")
    print()


def example_contact_filtering():
    """Example: Contact filtering."""
    print("👥 Contact filtering examples")
    
    # Example: Whitelist specific contact
    contact_filter = ContactFilter(
        inbound_behavior="whitelist",
        inbound_ids=["+1234567890"]
    )
    
    config = Config.default()
    config.contacts = contact_filter
    
    monitor = iMessageMonitor()
    monitor.config = config
    messages = monitor.get_recent_messages(limit=10)
    
    print(f"Filtered messages: {len(messages)}")
    for msg in messages[:3]:
        sender = msg.get('handle_id_str', 'Unknown')
        content = msg.get('message_text') or '[Media]'
        print(f"  • {sender}: {content[:50]}...")
    print()


def example_pretty_printing():
    """Example: Pretty message display."""
    print("🎨 Pretty printing example")
    
    monitor = iMessageMonitor()
    messages = monitor.get_recent_messages(limit=5)
    
    if messages:
        print("Sample message bubble:")
        print(pretty_print_bubble(messages[0]))
    print()


def example_batched_iterator():
    """Example: Iterate through messages with batch size 1."""
    print("🔄 Batched iterator example (batch_size=1)")
    
    # Override config to set batch size to 1
    config = Config.default()
    config.monitoring.max_batch_size = 1
    
    monitor = iMessageMonitor()
    monitor.config = config
    
    print("Getting last 10 messages, one at a time:")
    message_count = 0
    for batch in monitor.get_recent_messages_batched(limit=10):
        for message in batch:
            message_count += 1
            sender = "You" if message.get('is_from_me') else message.get('handle_id_str', 'Unknown')
            content = message.get('message_text') or '[Media]'
            print(f"  Message {message_count}: {sender} - {content[:30]}...")
    
    print(f"Processed {message_count} messages in individual batches")
    print()


async def main():
    """Run all examples."""
    print("iMessage Monitor - Examples\n")
    
    # Quick examples
    example_recent_messages()
    example_contact_filtering()
    example_pretty_printing()
    example_batched_iterator()
    
    # Real-time example (uncomment to run)
    await example_real_time_monitoring()
    
    # Interactive option
    print("🎯 Try it out!")
    choice = input("Enter phone number to send welcome message (or press Enter to exit): ").strip()
    
    if choice:
        try:
            from imessage_monitor.outbound import AppleScriptSender
            sender = AppleScriptSender()
            message = "AppleScript welcomes you to imessage-monitor!"
            
            print(f"Sending welcome message to {choice} using AppleScript ...")
            success = await sender.send_text_message(choice, message)
            
            if success:
                print("✅ Message sent successfully!")
            else:
                print("❌ Failed to send message")
        except Exception as e:
            print(f"❌ Error sending message: {e}")
    
        try:
            from imessage_monitor.outbound import ShortcutsSender
            sender = ShortcutsSender()
            message = "Shortcuts welcomes you to imessage-monitor!"
            
            print(f"Sending welcome message to {choice} using Shortcuts ...")
            success = await sender.send_text_message(choice, message)
            
            if success:
                print("✅ Message sent successfully!")
            else:
                print("❌ Failed to send message")
        except Exception as e:
            print(f"❌ Error sending message: {e}")

    print("👋 Goodbye!")


if __name__ == "__main__":
    asyncio.run(main())