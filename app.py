import os
import json
import PyPDF2
import anthropic
import chainlit as cl
from dotenv import load_dotenv
from supabase import create_client
import tempfile

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase = create_client(
    os.getenv("SUPABASE_URL", "https://bedfheavyxwknljzgmsy.supabase.co"),
    os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJlZGZoZWF2eXh3a25sanpnbXN5Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0Mzc2NzcwOSwiZXhwIjoyMDU5MzQzNzA5fQ.DSOp7pHDazVtmIj9pvMAFyP0OVSyliQXVnVydOQB_fk")
)

# Initialize Anthropic client
anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# System prompt for resume analysis
RESUME_ANALYSIS_SYSTEM_PROMPT = """
You are an expert resume analyzer that provides detailed, constructive feedback on resumes.

Your analysis should include:
1. Summary of the candidate's background, skills, and experience
2. Strengths of the resume
3. Areas for improvement (content, structure, formatting)
4. ATS optimization recommendations
5. Industry-specific advice based on the candidate's field
6. Suggestions for better highlighting achievements and impact
7. Recommendations for skills to develop or highlight based on current job market trends

Be specific, actionable, and supportive in your feedback. Provide examples where possible.
Format your response with clear headers and bullet points for readability.
"""

def store_github_user(github_user):
    """Store GitHub user in Supabase"""
    try:
        # Extract primary email from GitHub user data
        primary_email = None
        if "emails" in github_user and github_user["emails"]:
            for email in github_user["emails"]:
                if email.get("primary"):
                    primary_email = email.get("email")
                    break
        
        if not primary_email:
            # Fall back to login if no primary email found
            primary_email = f"{github_user['login']}@github.com"
        
        # Prepare user data
        user_data = {
            "github_id": str(github_user["id"]),
            "email": primary_email,
            "username": github_user["login"],
            "name": github_user.get("name") or github_user["login"],
            "avatar_url": github_user.get("avatar_url", ""),
            "last_login": "now()"
        }
        
        # Check if user exists by GitHub ID
        response = supabase.table("github_users").select("*").eq("github_id", str(github_user["id"])).execute()
        
        if len(response.data) > 0:
            # Update existing user
            print(f"Updating existing GitHub user: {user_data['username']}")
            supabase.table("github_users").update(user_data).eq("github_id", str(github_user["id"])).execute()
            return user_data
        else:
            # Create new user
            print(f"Creating new GitHub user: {user_data['username']}")
            supabase.table("github_users").insert(user_data).execute()
            return user_data
    except Exception as e:
        print(f"Error storing GitHub user in Supabase: {e}")
        return None

def extract_resume_text(file_content):
    """Extract text from a PDF resume content"""
    try:
        # Create a temporary file to handle the PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(file_content)
            temp_path = temp_file.name
        
        print(f"Reading resume from temporary file: {temp_path}")
        resume_text = ""
        with open(temp_path, "rb") as f:
            pdf_reader = PyPDF2.PdfReader(f)
            print(f"PDF loaded successfully. Pages found: {len(pdf_reader.pages)}")
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                page_text = page.extract_text()
                print(f"Page {page_num+1} extracted: {len(page_text)} characters")
                resume_text += page_text
        
        # Clean up the temporary file
        os.unlink(temp_path)
        
        if not resume_text.strip():
            raise Exception("Empty text extracted from PDF")
            
        print(f"Successfully extracted {len(resume_text)} characters from resume")
        return resume_text
    except Exception as e:
        print(f"Error extracting resume text: {e}")
        raise

def analyze_resume(resume_text, user_name=None):
    """Analyze resume using Anthropic's Claude"""
    try:
        system_prompt = RESUME_ANALYSIS_SYSTEM_PROMPT
        
        # Personalize the analysis if we have the user's name
        if user_name:
            system_prompt += f"\n\nYou're analyzing {user_name}'s resume. Address them by name in your feedback."
        
        # Send the resume text to Claude for analysis
        response = anthropic_client.messages.create(
            model="claude-3-7-sonnet-20240229",  # Using a specific version for stability
            system=system_prompt,
            messages=[
                {"role": "user", "content": f"Here is a resume to analyze:\n\n{resume_text}\n\nPlease provide detailed feedback."}
            ],
            max_tokens=4096,
            temperature=0.5
        )
        
        return response.content[0].text
    except Exception as e:
        print(f"Error analyzing resume: {e}")
        raise

@cl.oauth_callback
def oauth_callback(provider_id, token, raw_user_data):
    """Handle GitHub OAuth login"""
    try:
        print(f"OAuth callback called with provider: {provider_id}")
        
        if provider_id != "github":
            print(f"Unsupported provider: {provider_id}")
            return None
        
        # Store GitHub user data in Supabase
        user_data = store_github_user(raw_user_data)
        if not user_data:
            print("Failed to store GitHub user")
            return None
        
        # Create a unique identifier
        identifier = user_data["username"]
        
        # Return Chainlit user
        return cl.User(
            identifier=identifier,
            metadata={
                "name": user_data["name"],
                "image": user_data.get("avatar_url", ""),
                "provider": "github",
                "github_username": user_data["username"],
                "email": user_data["email"]
            }
        )
    except Exception as e:
        print(f"Error in OAuth callback: {e}")
        return None

@cl.on_chat_start
async def on_chat_start():
    # Check if user is authenticated
    user = cl.user_session.get("user")
    if not user:
        await cl.Message(
            content="Authentication required. Please log in with GitHub.",
            author="System",
        ).send()
        return
    
    # Extract user details
    user_identifier = user.identifier
    user_name = user.metadata.get("name", user_identifier)
        
    # Store user info in session
    cl.user_session.set("user_identifier", user_identifier)
    cl.user_session.set("user_name", user_name)
    
    # Welcome message
    welcome_msg = (
        f"# Resume Analyzer\n\n"
        f"Hello {user_name}! 👋\n\n"
        f"This tool will analyze your resume and provide detailed feedback to help you improve it. "
        f"Simply upload your resume as a PDF file, and I'll analyze it using Claude, a powerful AI assistant.\n\n"
        f"**How it works:**\n"
        f"1. Click the upload button below and select your resume (PDF format only)\n"
        f"2. Wait a few moments for the analysis to complete\n"
        f"3. Receive detailed feedback on your resume\n\n"
        f"Let's make your resume stand out!"
    )
    
    await cl.Message(content=welcome_msg, author="Resume Analyzer").send()

@cl.on_message
async def on_message(message: cl.Message):
    # Check if user is authenticated
    user = cl.user_session.get("user")
    user_identifier = cl.user_session.get("user_identifier")
    user_name = cl.user_session.get("user_name")
    
    if not user_identifier or not user:
        await cl.Message(
            content="Please log in with GitHub to continue.",
            author="System",
        ).send()
        return
    
    # Check if this is a file upload (PDF resume)
    if message.elements and any(elem.mime.endswith('/pdf') for elem in message.elements):
        # Process the resume
        await cl.Message(
            content="Analyzing your resume... This will take a few moments.",
            author="Resume Analyzer"
        ).send()

        try:
            # Get the first PDF file
            pdf_file = next(elem for elem in message.elements if elem.mime.endswith('/pdf'))
            
            # Read file content into memory
            with open(pdf_file.path, "rb") as f:
                file_content = f.read()

            # Extract text from PDF content
            resume_text = extract_resume_text(file_content)

            if not resume_text.strip():
                await cl.Message(
                    content="I couldn't extract text from this PDF. Please make sure it contains selectable text and not just images.",
                    author="Resume Analyzer"
                ).send()
                return

            # Send the resume text to Claude for analysis
            async with cl.Step(name="Analyzing resume..."):
                analysis_content = analyze_resume(resume_text, user_name)

            # Store in session
            cl.user_session.set("resume_text", resume_text)
            cl.user_session.set("previous_analysis", analysis_content)
            
            # Send the analysis
            await cl.Message(
                content=analysis_content,
                author="Resume Analyzer"
            ).send()

            # Ask if they want more specific advice
            await cl.Message(
                content="Would you like more specific advice on a particular section of your resume? For example, you can ask about your summary, work experience, skills section, or formatting.",
                author="Resume Analyzer"
            ).send()

        except Exception as e:
            error_msg = f"Sorry, I ran into an issue analyzing the resume: {str(e)}. Please try again or upload a different PDF."
            await cl.Message(
                content=error_msg,
                author="Resume Analyzer"
            ).send()
    else:
        # Handle follow-up questions about the resume
        try:
            # Check if we have resume data in the session
            resume_text = cl.user_session.get("resume_text")
            previous_analysis = cl.user_session.get("previous_analysis")
            
            if not resume_text or not previous_analysis:
                await cl.Message(
                    content="I don't see any resume you've uploaded yet. Please upload your resume as a PDF file first.",
                    author="Resume Analyzer"
                ).send()
                return
            
            # Create a contextual system prompt for follow-up questions
            follow_up_system_prompt = f"""
            You are an expert resume analyzer providing follow-up advice on a resume.
            
            You have previously analyzed this resume and provided the following feedback:
            
            {previous_analysis}
            
            Now, answer the user's specific question about their resume with detailed, actionable advice.
            Keep your response focused on their specific question while leveraging your knowledge of their resume.
            If appropriate, refer to specific parts of their resume in your answer.
            
            The full text of their resume is:
            
            {resume_text}
            """
            
            # Generate response to the follow-up question
            async with cl.Step(name="Answering your question..."):
                follow_up_response = anthropic_client.messages.create(
                    model="claude-3-7-sonnet-20240229",  # Using a specific version for stability
                    system=follow_up_system_prompt,
                    messages=[
                        {"role": "user", "content": message.content}
                    ],
                    max_tokens=4096,
                    temperature=0.5
                )
            
            # Send the follow-up response
            follow_up_content = follow_up_response.content[0].text
            await cl.Message(
                content=follow_up_content,
                author="Resume Analyzer"
            ).send()
            
        except Exception as e:
            error_msg = f"Sorry, I ran into an issue while processing your question: {str(e)}. Please try again."
            await cl.Message(
                content=error_msg,
                author="Resume Analyzer"
            ).send()

# Entry point for Chainlit app
if __name__ == "__main__":
    cl.run()