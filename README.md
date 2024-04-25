---

# Trixie

Trixie is an application that leverages AI to engage in conversations and provide information to users based on specific commands. It aims to deliver a personalized and interactive experience, utilizing various AI models for different functionalities.

## Usage

To run Trixie, please follow these instructions:

1. **Install Dependencies**: Ensure that all required dependencies are installed. You can install them using the following command:
   
   ```
   pip install -r requirements.txt
   ```

2. **Run the Application**: Execute the `main.py` file to start Trixie.
   
   ```
   python main.py
   ```

## Commands

Trixie supports the following commands:

1. **Open**: Initiates any application in the machine.
   
2. **Search**: `search [topic]` - Enables users to search Wikipedia for information on a given topic. Trixie utilizes wikipedia api to fetch relevant information and provide it to the user.
   
3. **Remember**: `remember [data]` - Allows users to input data that Trixie can store for future reference. This feature is useful for keeping track of important information.
   
4. **Retrieve**: `retrieve` - Retrieves and displays data from the last three retrieved files. Users can easily access recently retrieved information.
   
5. **What is / Explain**: `what is [query]` / `explain [query]` - Utilizes a language model to provide detailed explanations or definitions based on user queries. Trixie can answer questions and explain concepts.
   
6. **Write a**: `write a [task]` - Employs a code model to generate code snippets based on user input. This feature assists users in quickly generating code for various tasks.
   
7. **Image**: `image [path_to_image]` - Utilizes an image model to describe uploaded images. Users can upload images, and Trixie will provide descriptions or information related to the content of the image.

These functionalities are activated based on specific commands detected through speech recognition, making interaction with Trixie seamless and intuitive.

## Goal

The primary objective of Trixie is to create a highly personalized and interactive application for users. By leveraging cutting-edge AI technologies, Trixie aims to enhance user engagement and utility. Whether it's retrieving information, generating code snippets, or providing descriptions for images, Trixie strives to deliver a seamless user experience tailored to individual preferences.

---
