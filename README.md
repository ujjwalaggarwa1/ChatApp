# *ChatApp*

It is a secure terminal chat app that is made on `python`. It follows `end to end encryption` to let someone chat securely

> Quick note: `I made this project myself` and used AI only for the idea of the project and some minor explanation of module functions

- documented use of AI
    - The testing file was made by AI because i got tired
    - It was used for debugging when it was time for ui and backend integration

---
---
>## Features
1. End to end encryption
2. RSA and AES encryptions
3. Multi device connectivity
4. ~~In memory cache system to automatically resend undelivered messages~~ : 
    - While researching on how other applications manage cache, i got to know that tcp will deliver the messages and does the purpose of this feature automatically so the `idea is dropped`
5. Good terminal UI
6. A logging system for debugging the code (i just used the logger from of my previous projects)

>## External Libraries
1. pycryptodome
2. textual

- run :- `pip install -r requirements.txt`
- note :- The file was made in virtual environment and it is advised to use one

>## Learnt Values
- Sockets Library
- Encryption basics
- Asynchronous Scripts
- Network Protocols and working
- Textual Library

>## Techstack
1. Python
2. socket library
3. RSA and AES
4. Textual library

>## References

- ### Markdown
1. [Markdown Cheatsheet](https://www.markdownguide.org/cheat-sheet/)

- ### Git & Github
1. [Youtube - Git & GitHub Crash Course for Beginners [2026]](https://youtu.be/mAFoROnOfHs?si=RdDRp12HVZnnrYfd)
2. [Youtube - Git & GitHub For First Year Students (What Actually Matters)](https://youtu.be/BnEFaIfcwOU?si=20hrfd0fUuGInQ3_)
3. [Online Notes](https://41chaitanya.github.io/git_github_notes/)

- ### Socket Library and Networks
1. [Youtube - Python Socket Programming](https://youtube.com/playlist?list=PLS1QulWo1RIZGSgRsn0b8w9uoWM1gHDpo&si=Zbx3krBG2BaX1LKg)
2. [W3schools - socket](https://www.w3schools.com/python/ref_module_socket.asp)
3. [Youtube - Python Socket Programming Tutorial](https://youtu.be/3QiPPX-KeSc?si=pTXcGwN420-8Dl8_)

- ### AsyncIO
1. [Youtube - AsyncIO in Python | Python Tutorial](https://youtu.be/lgoB3_-ejnI?si=mkOKFpQmT5s7EJyU)
2. [W3schools - AsyncIO](https://www.w3schools.com/python/ref_module_asyncio.asp)

- ### Encryption
1. [Youtube - Asymmetric Encryption - Simply explained](https://youtu.be/AQDCe585Lnc?si=GUiClSys-Tp538Gt)
2. [Youtube - How Encryption Works](https://youtu.be/h1qf_tBaXtg?si=wfwHtqWXe5N1esV9)

- ### PyCryptodome
1. [PyCryptodome official documentation](https://pycryptodome.readthedocs.io/en/latest/src/public_key/rsa.html)
2. [Youtube - PyCryptodome Encryption Tutorial (RSA + OAEP Explained)](https://youtu.be/RUKSXz7Ixsc?si=Rj6Iv0w753FlV0hz)

- ### Textual
1. [Youtube - Building UIs in the Terminal With Python Textual: Your First TUI, Text Widgets & TCSS](https://youtu.be/dpJrM2_NOT8?si=EX3Mxg6mfY9ElcNx)
2. [Textual official Documentation](https://textual.textualize.io/api/)