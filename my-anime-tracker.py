#!/usr/bin/env python3

"""
Advanced Anime Watchlist Tracker
A feature-rich terminal application for managing your anime collection
"""

import json
import os
import sys
import hashlib
import getpass
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC #password based key verifiaction function 2

# First try to import rich normally
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.text import Text
    from rich import box
    from rich.align import Align
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# If rich is not available, try to install it
if not RICH_AVAILABLE:
    print("Installing required packages...")
    os.system("pip install rich cryptography")
    # Try importing again after installation
    try:
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        from rich.prompt import Prompt, Confirm
        from rich.progress import Progress, SpinnerColumn, TextColumn
        from rich.text import Text
        from rich import box
        from rich.align import Align
        RICH_AVAILABLE = True
    except ImportError:
        print("Failed to install required packages. Please run: pip install rich cryptography")
        sys.exit(1)

# Now we can safely create the console instance
console = Console()

class AnimeTracker:
    def __init__(self):
        #create data directory in user's home folder
        self.app_dir = os.path.join(os.path.expanduser("~"), ".Anime")
        self.ensure_data_directory()

        self.data_file = os.path.join(self.app_dir, "data.enc")
        self.config_file = os.path.join(self.app_dir, "config.json")
        self.exports_dir = os.path.join(self.app_dir, "exports")

        self.adult_password_hash = None
        self.encryption_key = None
        self.data = {
            "anime_list": [],
            "adult_content": [],
            "stats": {
                "total_episodes_watched": 0,
                "total_hours_watched": 0,
                "favorite_genres": {},
                "completion_role": 0
            }
        }
        self.load_config()
        self.initialize_encryption()

    def ensure_data_directory(self):
        """Create application data directory if it doesn't exists"""
        try:
            if not os.path.exists(self.app_dir):
                os.makedirs(self.app_dir)
                console.print(f"[green]✓ Created data directory: {self.app_dir}[/green]")

            #create exports subdirectory
            exports_path = os.path.join(self.app_dir, "exports")
            if not os.path.exists(exports_path):
                os.makedirs(exports_path)
        
        except Exception as e:
            console.print(f"[red]Error creating data directory: {e}[/red]")
            console.print(f"[yellow]Falling back to current directory[/yellow]")
            self.app_dir = "."

    def generate_key_from_password(self, password, salt) -> bytes:
        """Generate encryptuon key from the password"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def initialize_encryption(self):
        """Initialize encryption systems"""
        if not os.path.exists(self.config_file):
            password = getpass.getpass("Set master password for encryption: ")
            salt = os.urandom(16)
            self.encryption_key = self.generate_key_from_password(password, salt)

            #Save the salt for furture use
            recovery_key = Fernet.generate_key().decode()
            console.print("\n[bold yellow]IMPORTANT: Save this recovery key in a secure place![/bold yellow]")
            console.print(f"[bold]Recovery Key:[/bold] {recovery_key}")
            console.print("[yellow]Without this key, you may lose access to your data if you forget your password![/yellow]")
            self.security_questions = []

            # Optionally set security questions
            if Confirm.ask("\nWould you like to set up security questions for additional recovery options?"):
                self.setup_security_question()

            config = {
                "salt": base64.b64encode(salt).decode(),
                "recovery_key_hash": self.hash_password(recovery_key),
                "adult_password_hash": None,
                "security_questions": getattr(self, 'security_questions', None)
            }
            with open(self.config_file, 'w') as f:
                json.dump(config, f)
        else:
            self.load_encryption()
    
    def load_encryption(self):
        with open(self.config_file, 'r') as f:
            config = json.load(f)
        
        try:
            password = getpass.getpass("Enter master password (or press enter for recovery options):")
            if password:
                salt = base64.b64decode(config["salt"])
                self.encryption_key = self.generate_key_from_password(password, salt)
                if os.path.exists(self.data_file):
                    with open(self.data_file,'rb') as f:
                        encrypted_data = f.read()
                    self.decrypt_data(encrypted_data)
                return
        except:
            pass
        console.print("\n[bold red]Password incorrect or forgotten[/bold red]")
        if config.get("recovery_key_hash"):
            if Confirm.ask("Would you like to use your recovery key?"):
                recovery_key = Prompt.ask("Enter your recovery key")
                if self.hash_password(recovery_key) == config["recovery_key_hash"]:
                    console.print("[green]✓ Recovery key accepted![/green]")
                    # Generate new password
                    self.reset_password()
                    return
                
        if config.get("security_questions"):
            if Confirm.ask("Would you like to answer security questions to reset your password?"):
                if self.verify_security_questions(config["security_questions"]):
                    self.reset_password()
                    return
    
        console.print("[red]No valid recovery method available. Access denied.[/red]")
        sys.exit(1)

    def setup_security_question(self):
        questions = [
            "What city were you born in ?",
            "What was the name of your first pet ?",
            "What was your mother's maiden name?"
        ]
        self.security_questions = []
        console.print("\n[bold]Set up security questions[/bold]")
        console.print("[yellow]These will be used to verify your identity if you forget your password.[/yellow]")

        for i, question in enumerate(questions[:2]):
            answer = Prompt.ask(f"Question {i+1}: {question}")
            self.security_questions.append({
                "question": question,
                "answer_hash": self.hash_password(answer.lower().strip())
            })
    
    def verify_security_questions(self, stored_questions):
        console.print("\n[bold]Answer your security questions[/bold]")
        for i, question_data in enumerate(stored_questions):
            answer = Prompt.ask(f"Question {i+1}: {question_data['question']}").lower().strip()
            if self.hash_password(answer) != question_data["answer_hash"]:
                console.print("[red]Incorrect answer![/red]")
                return False
        return True

    def reset_password(self):
        config = {}
        with open(self.config_file, 'r') as f:
            config = json.load(f)
    
        console.print("\n[bold]Setting new master password[/bold]")
        new_password = getpass.getpass("Enter new master password: ")
        confirm_password = getpass.getpass("Confirm new master password: ")
    
        if new_password != confirm_password:
            console.print("[red]Passwords don't match![/red]")
            return False
    
        salt = base64.b64decode(config["salt"])
        self.encryption_key = self.generate_key_from_password(new_password, salt)
    
        # Re-encrypt data with new password if it exists
        if os.path.exists(self.data_file):
            with open(self.data_file, 'rb') as f:
                encrypted_data = f.read()
            decrypted_data = self.decrypt_data(encrypted_data)
            self.save_data()  # Will encrypt with new key
    
        console.print("[green]✓ Password changed successfully![/green]")
        return True

    def load_config(self):
        """Load configuration file data"""
        if os.path.exists(self.config_file):
            try:
               with open(self.config_file, 'r') as f:
                   config = json.load(f)
                   self.adult_password_hash = config.get("adult_password_hash")
                   if not hasattr(self, 'security_questions'):
                       self.security_questions = config.get('security_questions', [])
            except Exception as e:
                console.print(f"[red]Error loading config: {e}[/red]")
                self.adult_password_hash = None
                self.security_questions = []
               
    def save_config(self):
        """save config file data"""
        with open(self.config_file, 'r') as f:
            config = json.load(f)
        config["adult_password_hash"] = self.adult_password_hash
        with open(self.config_file, 'w') as f:
            json.dump(config, f)

    def encrypt_data(self, data) -> bytes:
        f = Fernet(self.encryption_key)
        return f.encrypt(data.encode())
    
    def decrypt_data(self, encrypted_data) -> str:
        f = Fernet(self.encryption_key)
        return f.decrypt(encrypted_data).decode()
    
    def save_data(self):
        try:
            json_data = json.dumps(self.data, indent=2)
            encrypted_data = self.encrypt_data(json_data)
            with open(self.data_file, 'wb') as f:
                f.write(encrypted_data)
        except Exception as e:
            console.print(f"[red]Error saving data: {e}[/red]")
            
    def load_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'rb') as f:
                    encrypted_data = f.read()
                decrypted_data = self.decrypt_data(encrypted_data)
                self.data = json.loads(decrypted_data)
            except Exception as e:
                console.print(f"[red]Error loading data (wrong password?): {e}[/red]")
                sys.exit(1)

    def hash_password(self, password) -> str:
        return hashlib.sha256(password.encode()).hexdigest()
    
    def setup_adult_password(self):
        """Improved adult password setup with confirmation and masking"""
        if self.adult_password_hash is None:
            console.print("\n[bold]Set Adult Content Password[/bold]")
        
            while True:
                password = getpass.getpass("Set password for adult content access: ")
                confirm = getpass.getpass("Confirm password: ")
            
                if password == confirm:
                    if len(password) < 8:
                        console.print("[red]Password must be at least 8 characters![/red]")
                        continue
                    
                    self.adult_password_hash = self.hash_password(password)
                    self.save_config()
                
                    # Optionally set security questions
                    if Confirm.ask("\nSet security questions for adult content password recovery?"):
                        self.setup_adult_security_questions()
                
                    console.print("[green]✓ Adult content password set![/green]")
                    return True
                else:
                    console.print("[red]Passwords don't match! Try again[/red]")
        return False

    def verify_adult_password(self) -> bool:
        """Improved verification with attempts limit"""
        if self.adult_password_hash is None:
            return self.setup_adult_password()
    
        attempts = 3
        while attempts > 0:
            password = getpass.getpass("Enter adult content password: ")
            if self.hash_password(password) == self.adult_password_hash:
                return True
            
            attempts -= 1
            if attempts > 0:
                console.print(f"[red]Incorrect password! {attempts} attempts remaining[/red]")
    
        console.print("[red]Access denied![/red]")
    
        # Optional recovery path
        if hasattr(self, 'adult_security_questions'):
            if Confirm.ask("Forgot password? Try security questions"):
                return self.verify_adult_security_questions()
    
        return False

    def setup_adult_security_questions(self):
        """Separate security questions just for adult content"""
        questions = [
            "What was your first adult anime?",
            "What fictional character do you find most attractive?",
            "Your secret code word for adult content?"
        ]
    
        self.adult_security_questions = []
        console.print("\n[bold]Adult Content Security Questions[/bold]")
    
        for i, question in enumerate(questions[:2]):
            answer = Prompt.ask(f"Question {i+1}: {question}", password=True)
            self.adult_security_questions.append({
                "question": question,
                "answer_hash": self.hash_password(answer.lower().strip())
            })
    
        # Save to config
        with open(self.config_file, 'r') as f:
            config = json.load(f)
        config["adult_security_questions"] = self.adult_security_questions
        with open(self.config_file, 'w') as f:
            json.dump(config, f)

    def verify_adult_security_questions(self) -> bool:
        """Verify adult content security questions"""
        if not hasattr(self, 'adult_security_questions'):
            console.print("[red]No recovery options available[/red]")
            return False
    
        console.print("\n[bold]Adult Content Recovery[/bold]")
        for i, q in enumerate(self.adult_security_questions[:2]):
            answer = Prompt.ask(f"Q{i+1}: {q['question']}", password=True)
            if self.hash_password(answer.lower().strip()) != q["answer_hash"]:
                console.print("[red]Verification failed![/red]")
                return False
        return True
    
    def add_anime(self, adult_mode=False):
        """Add a new anime to the files"""
        console.print(Panel.fit("📝 Add New Anime", style="bold blue"))

        anime = {}
        anime["id"] = len(self.data["anime_list"]) + len(self.data["adult_content"]) + 1
        anime["title"] = Prompt.ask("Anime Title")
        anime["genre"] = Prompt.ask("Genre", default="Unknown")
        anime["status"] = Prompt.ask("Status", choices=["Watching", "Completed", "On Hold", "Dropped", "Plan to Watch"], default="Plan to Watch")
        anime["episodes_watched"] = int(Prompt.ask("Episodes Watched", default="0"))
        anime["total_episodes"] = int(Prompt.ask("Total Episodes", default="1"))

        if int(anime["episodes_watched"]) > int(anime['total_episodes']):
            console.print(Panel.fit("Total episodes can't be less than episodes watched"))
            return
        
        anime["rating"] = float(Prompt.ask("Your Rating (1-10)", default="0"))

        if int(anime["rating"]) > 10 or int(anime["rating"]) < 0:
            console.print(Panel.fit("Total episodes can't be less than episodes watched"))
            return
        
        anime["notes"] = Prompt.ask("Notes", default="")
        anime["date_added"] = datetime.now().strftime("%Y-%m-%d")
        anime["last_watched"] = datetime.now().strftime("%Y-%m-%d") if anime["episodes_watched"] > 0 else ""

        if adult_mode:
            anime["adult_content"] = True
            self.data["adult_content"].append(anime)
        else:
            anime["adult_content"] = False
            self.data["anime_list"].append(anime)
        
        self.update_stats()
        self.save_data()
        console.print(f"[green]✓ Added '{anime['title']}' to your list![/green]")

    def update_stats(self, include_adult=False):
        """Update statistics, optionally including adult content"""
        # Use only normal anime by default
        anime_to_analyze = self.data["anime_list"].copy()
    
        # Include adult content if requested and password verified
        if include_adult and self.verify_adult_password():
            anime_to_analyze.extend(self.data["adult_content"])
    
        total_episodes = sum(anime["episodes_watched"] for anime in anime_to_analyze)
        total_hours = total_episodes * 24 / 60  # Assuming 24 minutes per episode

        genre_count = {}
        completed_count = 0
    
        for anime in anime_to_analyze:
            # Count genres
            genres = anime["genre"].split(", ")
            for genre in genres:
                genre_count[genre] = genre_count.get(genre, 0) + 1

                # Count completed
                if anime["status"] == "Completed":
                    completed_count += 1

        completion_rate = (completed_count / len(anime_to_analyze) * 100) if anime_to_analyze else 0

        self.data["stats"] = {
            "total_episodes_watched": total_episodes,
            "total_hours_watched": round(total_hours, 1),
            "favorite_genres": genre_count,
            "completion_rate": round(completion_rate, 1),
            "total_anime": len(anime_to_analyze),
            "completed_anime": completed_count,
            "includes_adult": include_adult  # Track if stats include adult content
        }

    def display_anime_list(self, adult_mode=False):
        anime_list = self.data["adult_content"] if adult_mode else self.data["anime_list"]

        if not anime_list:
            console.print(Panel.fit("No anime in your list yet! Add some with 'add' command.", style="yellow"))
            return
        
        table = Table(title=f"🎌 {'Adult Content' if adult_mode else 'Anime Watchlist'} 🎌", box=box.ROUNDED)
        table.add_column("ID", justify="center", style="cyan", min_width=3)
        table.add_column("Title", style="magenta", min_width=20)
        table.add_column("Genre", style="green", min_width=15)
        table.add_column("Status", justify="center", min_width=12)
        table.add_column("Progress", justify="center", style="yellow", min_width=10)
        table.add_column("Rating", justify="center", style="red", min_width=6)
        table.add_column("Last Watched", justify="center", style="blue", min_width=12)

        for anime in sorted(anime_list, key=lambda x:x.get("last_watched", ""), reverse=True):
            #color coding for status
            status_colors = {
                "Watching": "[green]Watching[/green]",
                "Completed": "[blue]Completed[/blue]",
                "On Hold": "[yellow]On Hold[/yellow]",
                "Dropped": "[red]Dropped[/red]",
                "Plan to Watch": "[white]Plan to Watch[/white]"
            }

            progress = f"{anime['episodes_watched']}/{anime['total_episodes']}"
            if anime['episodes_watched'] == anime['total_episodes'] and anime['total_episodes'] > 0:
                progress = f"[green]{progress}[/green]"
            elif anime['episodes_watched'] > 0:
                progress = f"[yellow]{progress}[/yellow]"

            rating_display = f"⭐{anime['rating']}" if anime['rating'] > 0 else "Not Rated"
            table.add_row(
                str(anime["id"]),
                anime["title"],
                anime["genre"],
                status_colors.get(anime["status"], anime["status"]),
                progress,
                rating_display,
                anime.get("last_watched", "Never") or "Never"
            )

        console.print(table)
    
    def update_anime(self, adult_mode=False):
        anime_list = self.data["adult_content"] if adult_mode else self.data["anime_list"]
        if not anime_list:
            console.print("[yellow]No anime to update![/yellow]")
            return
        self.display_anime_list(adult_mode)
        try:
            anime_id = int(Prompt.ask("Enter the anime ID to upadate"))
            anime = next((a for a in anime_list if a["id"]==anime_id), None)

            if not anime:
                console.print("[red]Anime not found[/red]")
                return
            console.print(f"Updating: [magenta]{anime['title']}[/magenta]")

            field = Prompt.ask("What to update?", choices=["status", "episodes", "rating", "notes", "all"])
            if field in ["status", "all"]:
                anime["status"] = Prompt.ask("Status", choices=["Watching", "Completed", "On Hold", "Dropped", "Plan to Watch"], default=anime["status"])
            if field in ["episodes", "all"]:
                anime["episodes_watched"] = int(Prompt.ask("Episodes Watched", default=str(anime["episodes_watched"])))
                if anime["episodes_watched"] > 0:
                    anime["last_watched"] = datetime.now().strftime("%Y-%m-%d")

            if field in ["rating", "all"]:
                anime["rating"] = float(Prompt.ask("Rating (1-10)", default=str(anime["rating"])))
            
            if field in ["notes", "all"]:
                anime["notes"] = Prompt.ask("Notes", default=anime["notes"])
            
            self.update_stats()
            self.save_data()
            console.print("[green]✓ Anime updated successfully![/green]")
        except ValueError:
            console.print("[red]Invalid Input![/red]")

    def delete_anime(self, adult_mode=False):
        anime_list = self.data["adult_content"] if adult_mode else self.data["anime_list"]

        if not anime_list:
            console.print("[yellow]No anime to delete![/yellow]")
            return
        
        self.display_anime_list(adult_mode)

        try:
            anime_id = int(Prompt.ask("Enter anime ID to delete"))
            anime = next((a for a in anime_list if a["id"]==anime_id), None)

            if not anime:
                console.print("[red]Anime not found[/red]")
                return
            
            if Confirm.ask(f"Delete '[magenta]{anime['title']}[/magenta]'?"):
                anime_list.remove(anime)
                self.update_stats()
                self.save_data()
                console.print("[green]✓ Anime deleted successfully![/green]")
            
        except ValueError:
            console.print("[red]Invalid input![/red]")

    def show_stats(self):
        include_adult = False
    
        # Check if there is any adult content
        if self.data["adult_content"]:
            include_adult = Confirm.ask("Include adult content in statistics?", default=False)
    
         # Update stats based on user choice
        self.update_stats(include_adult=include_adult)
        stats = self.data["stats"]

        stats_table = Table(title="📊 Your Anime Statistics 📊", box=box.ROUNDED)
        stats_table.add_column("Metric", style="cyan", min_width=20)
        stats_table.add_column("Value", style="magenta", min_width=15)
        
        stats_table.add_row("Total Anime", str(stats.get("total_anime", 0)))
        stats_table.add_row("Completed Anime", str(stats.get("completed_anime", 0)))
        stats_table.add_row("Episodes Watched", str(stats["total_episodes_watched"]))
        stats_table.add_row("Hours Watched", f"{stats['total_hours_watched']} hours")
        stats_table.add_row("Completion Rate", f"{stats['completion_rate']}%")
        
        console.print(stats_table)
        #genres
        if stats['favorite_genres']:
            genre_table = Table(title="🎭 Favorite Genres 🎭", box=box.ROUNDED)
            genre_table.add_column("Genre", style="green")
            genre_table.add_column("Count", style="yellow", justify="center")
            
            sorted_genres = sorted(stats["favorite_genres"].items(), key=lambda x: x[1], reverse=True)
            for genre, count in sorted_genres[:5]:  # Top 5 genres
                genre_table.add_row(genre, str(count))
            
            console.print(genre_table)

    def search_anime(self, adult_mode=False):
        anime_list = self.data["adult_content"] if adult_mode else self.data["anime_list"]
        
        if not anime_list:
            console.print("[yellow]No anime to search![/yellow]")
            return
        
        query = Prompt.ask("Search by title or genre").lower()
        results = []

        for anime in anime_list:
            if (query in anime["title"].lower() or 
                query in anime["genre"].lower()):
                results.append(anime)
                
        if results:
            console.print(f"[green]Found {len(results)} results(s): [/green]")

            #a temp data to view data
            temp_data = {"anime_list": results, "adult_content": []}
            original_data = self.data
            self.data = temp_data
            self.display_anime_list(False)
            self.data = original_data
        else:
            console.print("[yellow]No results found![/yellow]")

    def export_data(self):
        exports_dir = os.path.join(self.app_dir, "exports")
        if not os.path.exists(exports_dir):
            os.makedirs(exports_dir)

        filename = os.path.join(exports_dir, f"anime_exports_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        #without adult content unless requested
        export_data = {
            "anime_list": self.data["anime_list"],
            "stats": self.data["stats"],
            "export_date": datetime.now().isoformat(),
            "export_info": {
                "total_anime": len(self.data["anime_list"]),
                "total_adult_content": len(self.data["adult_content"]),
                "app_version": "1.0.0"
            }
        }
        if Confirm.ask("Include adult content in export?"):
            if self.verify_adult_password():
                export_data["adult_content"] = self.data["adult_content"]
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            console.print(f"[green]✓ Data exported to:[/green]")
            console.print(f"[cyan]{filename}[/cyan]")
            
        except Exception as e:
            console.print(f"[red]Error exporting data: {e}[/red]")
    
    def import_data(self):
        exports_dir = os.path.join(self.app_dir, "exports")
        if not os.path.exists(exports_dir):
            console.print("[yellow]No exports directory found![/yellow]")
            return
        
        export_files = [f for f in os.listdir(exports_dir) if f.endswith('.json')]

        if not export_files:
            console.print("[yellow]No export files found![/yellow]")
            return
        
        console.print("[cyan]Available export files:[/cyan]")
        for i, filename in enumerate(export_files, 1):
            console.print(f"{i}. {filename}")
        
        try:
            choice = int(Prompt.ask("Select the file number")) - 1
            if 0 <= choice < len(export_files):
                filename = os.path.join(exports_dir, export_files[choice])

                with open(filename, 'r', encoding='utf-8') as f:
                    import_data = json.load(f)
                #merge or replace data
                merge_option = Prompt.ask("Import option", choices=["merge", "replace"], default="merge")
                
                if merge_option == "replace":
                    if Confirm.ask("This will replace all current data. Continue?"):
                        self.data["anime_list"] = import_data.get("anime_list", [])
                        if "adult_content" in import_data:
                            if self.verify_adult_password():
                                self.data["adult_content"] = import_data.get("adult_content", [])
                else:
                    #merge data
                    current_ids = {anime["id"] for anime in self.data["anime_list"] + self.data["adult_content"]}
                    next_id = max(current_ids) + 1 if current_ids else 1

                    for anime in import_data.get("anime_list", []):
                        anime["id"] = next_id
                        next_id+=1
                        self.data["anime_list"].append(anime)
                    
                    if "adult_content" in import_data:
                        if self.verify_adult_password():
                            for anime in import_data.get("adult_content",[]):
                                anime["id"] = next_id
                                next_id += 1
                                self.data["adult_content"].append(anime)
                
                self.update_stats()
                self.save_data()
                console.print("[green]✓ Data imported successfully![/green]")
        except (ValueError, IndexError):
            console.print("[red]Invalid selection![/red]")
        except Exception as e:
            console.print(f"[red]Error importing data: {e}[/red]")

    def create_backup(self):
        backup_dir = os.path.join(self.app_dir, "backups")
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(backup_dir, f"backup_{timestamp}.json")

        backup_data = {
            "anime_list": self.data["anime_list"],
            "adult_content": self.data["adult_content"],
            "stats": self.data["stats"],
            "backup_date": datetime.now().isoformat(),
            "backup_info": {
                "total_anime": len(self.data["anime_list"]),
                "total_adult_content": len(self.data["adult_content"]),
                "app_version": "1.0.0"
            }
        }

        try:
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            console.print(f"[green]✓ Backup created:[/green]")
            console.print(f"[cyan]{backup_file}[/cyan]")
            
        except Exception as e:
            console.print(f"[red]Error creating backup: {e}[/red]")

    def show_app_info(self):
        info_table = Table(title="📱 App Information 📱", box=box.ROUNDED)
        info_table.add_column("Property", style="cyan", min_width=20)
        info_table.add_column("Value", style="magenta", min_width=30)
        
        info_table.add_row("Version", "1.0.0")
        info_table.add_row("Data Directory", self.app_dir)
        info_table.add_row("Config File", "config.json")
        info_table.add_row("Data File", "anime_data.enc")
        info_table.add_row("Exports Directory", os.path.join(self.app_dir, "exports"))
        info_table.add_row("Backups Directory", os.path.join(self.app_dir, "backups"))
        
        #for file sizes
        try:
            if os.path.exists(self.data_file):
                size = os.path.getsize(self.data_file)
                info_table.add_row("Data File Size", f"{size:,} bytes")
        except:
            pass

        console.print(info_table)

    def display_all_anime(self, adult_mode=False):
        if adult_mode and not self.verify_adult_password():
            console.print("The Password is wrong, Try again.")
            return
        
        all_anime = self.data["anime_list"].copy()
        if adult_mode:
            all_anime.extend(self.data["adult_content"])

        if not all_anime:
            console.print(Panel.fit("no anime in your list yet!", style="yellow"))
            return
        table = Table(title="🎌 Complete Anime List 🎌", box=box.ROUNDED)
        table.add_column("ID", justify="center", style="cyan")
        table.add_column("Title", style="magenta")
        table.add_column("Type", style="dim", justify="center")
        table.add_column("Genre", style="green")
        table.add_column("Status", justify="center")
        table.add_column("Progress", justify="center", style="yellow")
        table.add_column("Rating", justify="center", style="red")

        for anime in sorted(all_anime, key=lambda x: x["id"]):
            #type of the anime
            anime_type = "🔞" if anime.get("adult_content", False) else "👶"
            status_colors = {
            "Watching": "[green]Watching[/green]",
            "Completed": "[blue]Completed[/blue]",
            "On Hold": "[yellow]On Hold[/yellow]",
            "Dropped": "[red]Dropped[/red]",
            "Plan to Watch": "[white]Plan to Watch[/white]"
        }
            #progress display
            progress = f"{anime['episodes_watched']}/{anime['total_episodes']}"
            if anime['episodes_watched'] == anime['total_episodes']:
                progress = f"[green]{progress}[/green]"
            elif anime['episodes_watched'] > 0:
                progress = f"[yellow]{progress}[/yellow]"
        
            table.add_row(
                str(anime["id"]),
                anime["title"],
                anime_type,
                anime["genre"],
                status_colors.get(anime["status"], anime["status"]),
                progress,
                f"⭐{anime['rating']}" if anime['rating'] > 0 else "Not Rated"
            )
    
        console.print(table)

    def show_help(self):
        help_text = f"""
[bold cyan]📺 Anime Watchlist Tracker Commands 📺[/bold cyan]

[yellow]Basic Commands:[/yellow]
• [green]add[/green] - Add new anime
• [green]list[/green] - Show anime list
• [green]update[/green] - Update anime info
• [green]delete[/green] - Remove anime
• [green]search[/green] - Search anime
• [green]stats[/green] - View statistics
• [green]list-all[/green] - View all Including Adults

[yellow]Adult Content Commands:[/yellow]
• [red]adult[/red] - Access adult content section
• [red]adult-add[/red] - Add adult anime
• [red]adult-list[/red] - Show adult anime list
• [red]adult-update[/red] - Update adult anime
• [red]adult-delete[/red] - Delete adult anime
• [red]adult-search[/red] - Search adult anime

[yellow]Utility Commands:[/yellow]
• [blue]export[/blue] - Export data to JSON
• [blue]import[/blue] - Import data from JSON
• [blue]backup[/blue] - Create backup
• [blue]info[/blue] - Show app info
• [blue]help[/blue] - Show this help
• [blue]quit[/blue] - Exit application

[bold blue]Data Location:[/bold blue]
[dim]{self.app_dir}[/dim]

[bold red]Note:[/bold red] Adult content requires password verification
        """
        console.print(Panel(help_text, title="Help Menu", border_style="blue"))


    def main_menu(self):
        self.load_data()

        welcome_banner = """
        
╔══════════════════════════════════════════════════════════════╗
║                 🎌 ANIME WATCHLIST TRACKER 🎌                ║
║                     Terminal Edition                         ║
╚══════════════════════════════════════════════════════════════╝
        """
        console.print(Text(welcome_banner, style="bold magenta"))
        console.print(Panel.fit("Type 'help' for commands or 'quit' to exit", style="dim"))

        while True:
            try:
                command = Prompt.ask("\n[bold cyan]AnimeTracker[/bold cyan]").lower().strip()
                if command == "quit" or command == "exit":
                    console.print("[green]Thanks for using Anime Tracker! 👋[/green]")
                    break
                elif command == "add":
                    self.add_anime()
                
                elif command == "list":
                    self.display_anime_list()
                
                elif command == "update":
                    self.update_anime()
                
                elif command == "delete":
                    self.delete_anime()
                
                elif command == "search":
                    self.search_anime()
                
                elif command == "stats":
                    self.show_stats()
                
                elif command == "export":
                    self.export_data()
                
                elif command == "import":
                    self.import_data()
                
                elif command == "backup":
                    self.create_backup()
                
                elif command == "info":
                    self.show_app_info()
                
                elif command == "help":
                    self.show_help()
                
                # Adult content commands
                elif command == "adult":
                    if self.verify_adult_password():
                        console.print("[red]🔞 Adult Content Mode Activated[/red]")
                        self.display_anime_list(adult_mode=True)
                
                elif command == "adult-add":
                    if self.verify_adult_password():
                        self.add_anime(adult_mode=True)
                
                elif command == "adult-list":
                    if self.verify_adult_password():
                        self.display_anime_list(adult_mode=True)
                
                elif command == "adult-update":
                    if self.verify_adult_password():
                        self.update_anime(adult_mode=True)
                
                elif command == "adult-delete":
                    if self.verify_adult_password():
                        self.delete_anime(adult_mode=True)
                
                elif command == "adult-search":
                    if self.verify_adult_password():
                        self.search_anime(adult_mode=True)

                elif command == "list-all":
                    self.display_all_anime(adult_mode=True)
                    
                else:
                    console.print("[red]Unknown command. Type 'help' for available commands.[/red]")
            except KeyboardInterrupt:
                 console.print("\n[yellow]Use 'quit' to exit properly.[/yellow]")
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")


if __name__ == "__main__":
    try:
        tracker = AnimeTracker()
        tracker.main_menu()
    except KeyboardInterrupt:
        console.print("\n[green]Goodbye! 👋[/green]")
    except Exception as e:
        console.print(f"[red]Fatal error: {e}[/red]")
        sys.exit(1)