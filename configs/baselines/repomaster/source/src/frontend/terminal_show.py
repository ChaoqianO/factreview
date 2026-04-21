#!/usr/bin/env python3
# -*- coding: utf-8 -*-


def print_repomaster_title():

    repomaster_logo = r"""
 ██████╗ ███████╗██████╗  ██████╗ ███╗   ███╗ █████╗ ███████╗████████╗███████╗██████╗ 
 ██╔══██╗██╔════╝██╔══██╗██╔═══██╗████╗ ████║██╔══██╗██╔════╝╚══██╔══╝██╔════╝██╔══██╗
 ██████╔╝█████╗  ██████╔╝██║   ██║██╔████╔██║███████║███████╗   ██║   █████╗  ██████╔╝
 ██╔══██╗██╔══╝  ██╔═══╝ ██║   ██║██║╚██╔╝██║██╔══██║╚════██║   ██║   ██╔══╝  ██╔══██╗
 ██║  ██║███████╗██║     ╚██████╔╝██║ ╚═╝ ██║██║  ██║███████║   ██║   ███████╗██║  ██║
 ╚═╝  ╚═╝╚══════╝╚═╝      ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝   ╚═╝   ╚══════╝╚═╝  ╚═╝"""
    
    subtitle = "🚀 Autonomous Exploration & Understanding of GitHub Repositories for Complex Task Solving"
    
    print("\033[36m" + repomaster_logo + "\033[0m")  # Cyan color for logo
    print()
    print("\033[33m" + subtitle.center(88) + "\033[0m")  # Yellow for subtitle
    print()    

def print_repomaster_cli():
    # ASCII Art for RepoMaster logo
    repomaster_logo = r"""
 ██████╗ ███████╗██████╗  ██████╗ ███╗   ███╗ █████╗ ███████╗████████╗███████╗██████╗ 
 ██╔══██╗██╔════╝██╔══██╗██╔═══██╗████╗ ████║██╔══██╗██╔════╝╚══██╔══╝██╔════╝██╔══██╗
 ██████╔╝█████╗  ██████╔╝██║   ██║██╔████╔██║███████║███████╗   ██║   █████╗  ██████╔╝
 ██╔══██╗██╔══╝  ██╔═══╝ ██║   ██║██║╚██╔╝██║██╔══██║╚════██║   ██║   ██╔══╝  ██╔══██╗
 ██║  ██║███████╗██║     ╚██████╔╝██║ ╚═╝ ██║██║  ██║███████║   ██║   ███████╗██║  ██║
 ╚═╝  ╚═╝╚══════╝╚═╝      ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝   ╚═╝   ╚══════╝╚═╝  ╚═╝
"""

    # Version and subtitle
    subtitle = "🚀 Autonomous Exploration & Understanding of GitHub Repositories for Complex Task Solving"
    version_info = "Version: 1.0.0 | Python 3.11+ | License: MIT"

    # Quick start section
    quick_start = """
╔═══════════════════════════════════ Quick Start ═══════════════════════════════════╗
║                                                                                    ║
║  🖥️  Frontend Mode (Web Interface):                                               ║
║      python launcher.py --mode frontend --streamlit-port 8501                     ║
║      Access: http://localhost:8501                                                ║
║                                                                                    ║
║  🤖 Backend Mode (Unified AI Assistant) ⭐ Recommended:                          ║
║      python launcher.py --mode backend --backend-mode unified                     ║
║                                                                                    ║
║  📝 Shell Script Shortcuts:                                                       ║
║      bash run.sh frontend           # Launch web interface                        ║
║      bash run.sh backend unified    # Run unified assistant                       ║
║                                                                                    ║
╚════════════════════════════════════════════════════════════════════════════════════╝"""

    # Performance metrics
    performance = """
┌─────────────────────── Performance Benchmarks ─────────────────────────┐
│                                                                         │
│  📊 GitTaskBench Results:                                              │
│  ├─ Execution Rate: 75.92% (vs SWE-Agent: 44.44%)                     │
│  ├─ Task Pass Rate: 62.96% (vs OpenHands: 24.07%)                     │
│  └─ Token Usage:    154k   (95% reduction vs existing frameworks)     │
│                                                                         │
│  🏆 MLE-Bench Results:                                                 │
│  ├─ Valid Submissions: 95.45%                                          │
│  ├─ Medal Rate:        27.27%                                          │
│  └─ Gold Medals:       22.73%                                          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘"""

    # Core features
    features = """
╔══════════════════════════ ✨ Core Features ═══════════════════════════╗
║                                                                        ║
║  🔍 Intelligent Repository Search                                     ║
║     • Deep search algorithms based on task descriptions               ║
║     • Multi-round query optimization                                  ║
║     • Automated repository relevance analysis                         ║
║                                                                        ║
║  🏗️  Hierarchical Repository Analysis                                 ║
║     • Hybrid structural modeling (HCT, FCG, MDG)                      ║
║     • Core component identification                                   ║
║     • Intelligent context initialization                              ║
║                                                                        ║
║  🔧 Autonomous Exploration & Execution                                ║
║     • Granular code view at file/class/function levels                ║
║     • Smart dependency analysis and tracing                           ║
║     • Context-aware information selection                             ║
║                                                                        ║
╚════════════════════════════════════════════════════════════════════════╝"""

    # Example tasks
    examples = """
┌──────────────────────── Example Tasks ─────────────────────────┐
│                                                                 │
│  💡 Simple Tasks:                                               │
│  • "Extract all table data from this PDF as CSV"               │
│  • "Scrape product names and prices from this webpage"         │
│                                                                 │
│  🎯 Complex Tasks:                                              │
│  • "Transform portrait into Van Gogh oil painting style"       │
│  • "Auto-edit video, extract clips of specific person"         │
│  • "Train image classifier on CIFAR-10 with transfer learning" │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘"""

    # Configuration status
    config_status = """
╔═══════════════════════ Configuration Status ══════════════════════╗
║                                                                    ║
║  🔐 API Keys Configuration:                                       ║
║  ├─ OpenAI API:      [ ] Not configured                          ║
║  ├─ Claude API:      [ ] Not configured                          ║
║  ├─ DeepSeek API:    [ ] Not configured                          ║
║  ├─ Serper API:      [ ] Not configured (Required for web search) ║
║  └─ Jina API:        [ ] Not configured (Required for extraction) ║
║                                                                    ║
║  📝 Configure in: configs/.env or configs/oai_config.py          ║
║                                                                    ║
║  Press Enter to continue or 'q' to quit...                        ║
║                                                                    ║
╚════════════════════════════════════════════════════════════════════╝"""

    # Footer info
    footer = """
═══════════════════════════════════════════════════════════════════════════════
  📚 Documentation: https://github.com/QuantaAlpha/RepoMaster
  📧 Support: wanghuacan17@mails.ucas.ac.cn
  ⭐ Star us on GitHub if RepoMaster helps you!
═══════════════════════════════════════════════════════════════════════════════"""

    # Print everything with colors
    print("\033[36m" + repomaster_logo + "\033[0m")  # Cyan color for logo
    print("\033[33m" + subtitle.center(88) + "\033[0m")  # Yellow for subtitle
    # print("\033[90m" + version_info.center(88) + "\033[0m")  # Gray for version
    print("\033[32m" + quick_start + "\033[0m")  # Green for quick start
    return
    print()
    print("\033[34m" + performance + "\033[0m")  # Blue for performance
    print()
    print("\033[35m" + features + "\033[0m")  # Magenta for features
    print()
    print("\033[36m" + examples + "\033[0m")  # Cyan for examples
    print()
    print("\033[33m" + config_status + "\033[0m")  # Yellow for config
    print()
    print("\033[90m" + footer + "\033[0m")  # Gray for footer

def print_startup_banner():
    """Print beautiful startup banner for environment and configuration"""
    banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                          🚀 RepoMaster Initialization                        ║
╚══════════════════════════════════════════════════════════════════════════════╝"""
    print("\033[36m" + banner + "\033[0m")  # Cyan color

def print_environment_status(env_file_path: str = None, success: bool = True):
    """Print environment loading status with beautiful formatting"""
    if success and env_file_path:
        status_box = f"""
┌─────────────────────── Environment Setup ───────────────────────┐
│                                                                  │
│  ✅ Environment Variables Loaded Successfully                   │
│  📁 Config File: {env_file_path:<42} │
│  🔑 API Keys: SERPER_API_KEY, JINA_API_KEY                     │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘"""
        print("\033[32m" + status_box + "\033[0m")  # Green color
    else:
        error_box = """
┌─────────────────────── Environment Setup ───────────────────────┐
│                                                                  │
│  ❌ Environment Variables Loading Failed                        │
│  ⚠️  Please check your .env file configuration                  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘"""
        print("\033[31m" + error_box + "\033[0m")  # Red color

def print_api_config_status(api_type: str = None, success: bool = True, config_info: tuple = None):
    """Print API configuration status with beautiful formatting"""
    if success and api_type and config_info:
        config_name, config_details = config_info
        status_box = f"""
┌──────────────────────── API Configuration ──────────────────────┐
│                                                                  │
│  ✅ API Configuration Validated                                 │
│  🔧 Active Config: {config_name:<42} │
│  🤖 Model: {config_details.get('config_list', [{}])[0].get('model', 'N/A'):<49} │
│  🌐 Base URL: {config_details.get('config_list', [{}])[0].get('base_url', 'Default'):<44} │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘"""
        print("\033[32m" + status_box + "\033[0m")  # Green color
    else:
        error_box = """
┌──────────────────────── API Configuration ──────────────────────┐
│                                                                  │
│  ❌ API Configuration Check Failed                              │
│  ⚠️  Please configure your API keys in configs/oai_config.py    │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘"""
        print("\033[31m" + error_box + "\033[0m")  # Red color

def print_launch_config(config):
    """Print launch configuration with beautiful formatting"""
    # Determine mode description
    mode_desc = {
        'frontend': 'Web Interface Mode',
        'backend': 'Backend Service Mode'
    }.get(config.mode, config.mode)
    
    backend_desc = ""
    if hasattr(config, 'backend_mode'):
        backend_modes = {
            'unified': 'Unified Assistant (All Features)',
            'deepsearch': 'Deep Search Engine',
            'general_assistant': 'General Programming Assistant', 
            'repository_agent': 'Repository Task Handler'
        }
        backend_desc = backend_modes.get(config.backend_mode, config.backend_mode)
    
    # Build configuration display
    config_lines = [
        f"│  🎯 Mode: {mode_desc:<52} │"
    ]
    
    if backend_desc:
        config_lines.append(f"│  🤖 Backend: {backend_desc:<47} │")
    
    config_lines.extend([
        f"│  📁 Work Directory: {str(config.work_dir):<42} │",
        f"│  📊 Log Level: {config.log_level:<47} │"
    ])
    
    if hasattr(config, 'api_type'):
        config_lines.append(f"│  🔧 API Type: {config.api_type:<48} │")
        config_lines.append(f"│  🌡️  Temperature: {config.temperature:<45} │")
    
    if hasattr(config, 'streamlit_port'):
        config_lines.append(f"│  🌐 Streamlit Port: {config.streamlit_port:<42} │")
    
    # Calculate box width based on content
    max_width = max(len(line) for line in config_lines)
    
    config_box = f"""
┌──────────────────────── Launch Configuration ────────────────────┐
│                                                                  │
""" + "\n".join(config_lines) + f"""
│                                                                  │
└──────────────────────────────────────────────────────────────────┘"""
    
    print("\033[34m" + config_box + "\033[0m")  # Blue color

def print_service_starting(service_name: str, description: str = ""):
    """Print service starting message with beautiful formatting"""
    desc_line = f"│  📋 {description:<56} │" if description else ""
    
    service_box = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                            🚀 Starting Service                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  🎯 Service: {service_name:<58} ║
{f'║  📋 Description: {description:<54} ║' if description else '║' + ' ' * 78 + '║'}
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝"""
    
    print("\033[35m" + service_box + "\033[0m")  # Magenta color

def print_unified_mode_welcome(work_dir: str):
    """Print beautiful welcome message for unified mode"""
    work_dir = work_dir.replace("/huacan/", "/")
    welcome_box = f"""
╔═════════════════════════ ✨ Unified Assistant Ready ✨ ════════════════════════════╗
║                                                                                    ║
║  🏠 Work Directory                                                                 ║
║     └─ {work_dir:<66}
║                                                                                    ║
║  🎯 Integrated Features                                                            ║
║     ├─ 📁 GitHub & Local Repository Task Processing                               ║
║     ├─ 💻 General Programming Assistant & Code Writing                            ║
║     └─ 🔍 Deep Search & Web Information Retrieval                                 ║
║                                                                                    ║
║  💡 Quick Start Guide                                                              ║
║     ├─ Describe your task, system will auto-select the best approach             ║
║     ├─ Type 'quit', 'exit' or 'q' to exit anytime                                 ║
║     └─ Type 'history'/'clear' to view/clear chat history                          ║
║                                                                                    ║
╚════════════════════════════════════════════════════════════════════════════════════╝"""
    
    print("\033[32m" + welcome_box.lstrip() + "\033[0m")  # Green color

def print_mode_welcome(mode_name: str, work_dir: str, features: list, instructions: list):
    """Print beautiful welcome message for any mode"""
    # Calculate box width dynamically based on mode name and content
    work_dir = work_dir.replace("/huacan/", "/")
    
    min_width = 78  # Minimum box width
    title_content = f" 🌟 {mode_name} 🌟 "
    title_length = len(title_content)
    
    # Calculate required width: title + decorative borders
    required_width = max(min_width, title_length + 24)  # 24 for decorative equals signs
    
    # Ensure the width is even for symmetry
    if required_width % 2 != 0:
        required_width += 1
    
    required_width = required_width + 4
    
    # Calculate padding for title centering
    total_padding = required_width - title_length - 2  # 2 for the border characters ╔╗
    left_padding = total_padding // 2
    right_padding = total_padding - left_padding
    
    # Build title line  
    title_line = f"╔{'═' * left_padding}{title_content}{'═' * right_padding}╗"
    
    # Build features section
    features_lines = []
    for feature in features:
        features_lines.append(f"║     {feature:<{required_width-7}} ║")
    
    # Build instructions section  
    instructions_lines = []
    for instruction in instructions:
        instructions_lines.append(f"║     {instruction:<{required_width-7}} ║")
    
    # Build bottom border
    bottom_border = "╚" + "═" * (required_width - 1) + "╝"
    
    # Adjust work directory line with tree symbol
    work_dir_line = f"║     └─ {work_dir:<{required_width-11}} ║"
    
    welcome_box = f"""{title_line}
║{'':<{required_width-1}}║
║  🏠 Work Directory{'':<{required_width-22}}║
{work_dir_line}
║{'':<{required_width-2}}║
║  📋 Available Features{'':<{required_width-25}}║
""" + "\n".join(features_lines) + f"""
║{'':<{required_width-2}}║
║  💡 Usage Instructions{'':<{required_width-25}}║
""" + "\n".join(instructions_lines) + f"""
║{'':<{required_width-2}}║
{bottom_border}"""
    
    print("\033[32m" + welcome_box + "\033[0m")  # Green color

def print_optimized_startup_sequence(env_status: dict, api_status: dict, config):
    """Print optimized startup sequence: welcome -> initialization -> logo -> ready state"""
    import time
    import sys
    
    # Step 1: Print welcome message with quick start info
    welcome_header = "RepoMaster v1.0.0 - Autonomous Repository Explorer"
    print("\033[36m" + welcome_header + "\033[0m")
    print()
    
    # Print quick start box
    quick_start = """╔═══════════════════════════════════ Quick Start ═══════════════════════════════════╗
║                                                                                    ║
║  🖥️  Frontend Mode (Web Interface):                                               ║
║      python launcher.py --mode frontend --streamlit-port 8501                     ║
║      Access: http://localhost:8501                                                ║
║                                                                                    ║
║  🤖 Backend Mode (Unified AI Assistant) ⭐ Recommended:                          ║
║      python launcher.py --mode backend --backend-mode unified                     ║
║                                                                                    ║
║  📝 Shell Script Shortcuts:                                                       ║
║      bash run.sh frontend           # Launch web interface                        ║
║      bash run.sh backend unified    # Run unified assistant                       ║
║                                                                                    ║
╚════════════════════════════════════════════════════════════════════════════════════╝"""
    print("\033[32m" + quick_start + "\033[0m")
    print()
    
    # Step 2: Initialization steps
    print("\033[36m🔄 Initializing...\033[0m")
    print()
    
    # Step 1: Environment Setup
    if env_status['success']:
        env_file = env_status.get('file', 'system environment')
        step1_msg = f"[1/4] 📁 Environment Setup... ✅ Loaded from {env_file}"
        print("\033[32m" + step1_msg + "\033[0m")
    else:
        step1_msg = "[1/4] 📁 Environment Setup... ❌ Failed to load .env"
        print("\033[31m" + step1_msg + "\033[0m")
    
    time.sleep(0.3)
    
    # Step 2: API Configuration
    if api_status['success']:
        provider = api_status.get('provider', 'Unknown')
        model = api_status.get('model', '')
        model_info = f" {model}" if model and model != 'N/A' else ""
        step2_msg = f"[2/4] 🔑 API Configuration... ✅ {provider}{model_info}"
        print("\033[32m" + step2_msg + "\033[0m")
    else:
        step2_msg = "[2/4] 🔑 API Configuration... ❌ API keys not configured"
        print("\033[31m" + step2_msg + "\033[0m")
    
    time.sleep(0.3)
    
    # Step 3: Service Configuration
    mode_desc = {
        'frontend': 'Web Interface',
        'backend': 'Backend Service'
    }.get(config.mode, config.mode)
    
    backend_desc = ""
    if hasattr(config, 'backend_mode'):
        backend_modes = {
            'unified': 'Unified Assistant',
            'deepsearch': 'Deep Search',
            'general_assistant': 'Programming Assistant', 
            'repository_agent': 'Repository Agent'
        }
        backend_desc = f", {backend_modes.get(config.backend_mode, config.backend_mode)}"
    
    work_dir_short = str(config.work_dir)
    if len(work_dir_short) > 30:
        work_dir_short = "..." + work_dir_short[-27:]
    
    step3_msg = f"[3/4] ⚙️  Service Configuration... ✅ {mode_desc}{backend_desc}, Work: {work_dir_short}"
    print("\033[32m" + step3_msg + "\033[0m")
    
    time.sleep(0.3)
    
    # Step 4: Service Launch
    step4_msg = "[4/4] 🚀 Service Launch... ✅ Ready!"
    print("\033[32m" + step4_msg + "\033[0m")
    
    time.sleep(0.2)
    print()
    
    # Progress bar animation
    bar_length = 40
    for i in range(bar_length + 1):
        progress = "█" * i + "░" * (bar_length - i)
        percentage = int((i / bar_length) * 100)
        progress_line = f"[{progress}] {percentage}%"
        
        # Clear line and print progress
        sys.stdout.write(f"\r\033[36m{progress_line}\033[0m")
        sys.stdout.flush()
        time.sleep(0.02)
    
    print("\n")
    print()
    
    # Step 3: Print separator
    print("="*70)
    print()
    
    # Step 4: Print RepoMaster logo
    print_repomaster_title()

def print_progressive_startup_panel(env_status: dict, api_status: dict, config):
    """Print progressive startup panel with steps and progress bar - kept for backward compatibility"""
    print_optimized_startup_sequence(env_status, api_status, config)

def print_unified_startup_panel(env_status: dict, api_status: dict, config):
    """Print unified startup panel - wrapper for backward compatibility"""
    print_progressive_startup_panel(env_status, api_status, config)

if __name__ == "__main__":
    print_repomaster_title()
    
    # Test new progressive startup panel
    print("\n" + "="*70)
    print("Testing Progressive Startup Panel:")
    print("="*70)
    
    # Mock data for testing
    env_status = {
        'success': True,
        'file': '/data/huacan/Code/workspace/RepoMaster/configs/.env'
    }
    
    api_status = {
        'success': True,
        'provider': 'OpenAI',
        'model': 'gpt-4o'
    }
    
    class MockConfig:
        def __init__(self):
            self.mode = "backend"
            self.backend_mode = "unified"
            self.work_dir = "/data/huacan/Code/workspace/RepoMaster/coding"
            self.log_level = "INFO"
            self.api_type = "basic"
            self.temperature = 0.1
    
    # Test the new progressive startup panel
    print_progressive_startup_panel(env_status, api_status, MockConfig())
