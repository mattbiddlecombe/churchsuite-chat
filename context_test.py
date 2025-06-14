import requests
import json

def check_context():
    # Check if context7 server is running
    try:
        response = requests.get('http://localhost:3000/health')
        print(f"Context7 server status: {response.status_code}")
        
        # Check if we can access vault
        response = requests.get('http://localhost:3000/vault')
        print(f"Vault access status: {response.status_code}")
        
        # Check if we can access key files
        key_files = ['PLANNING.md', 'TASK.md', 'GLOBAL_RULES.md', 'DECISIONS.md']
        for file in key_files:
            try:
                with open(file, 'r') as f:
                    content = f.read()
                    print(f"Successfully read {file}")
            except Exception as e:
                print(f"Error reading {file}: {str(e)}")
        
    except Exception as e:
        print(f"Error checking context: {str(e)}")

if __name__ == "__main__":
    check_context()
