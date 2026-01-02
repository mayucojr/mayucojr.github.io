# Mario's Personal Website


### Getting Started

Open a terminal on your Mac by INSERT_PROCEDURE. Navigate to a desired folder/directory where you like to work from. This video can help for understanding how to do this. ON my machine for exmaple, starting from my home folder/directory:

```bash
gabe@gabe-XPS-13-9300:~$ ls
balenaEtcher  Downloads         Pictures          Templates
cmu           legion_essential  Public            Videos
Desktop       matlab_projects   snap              websites
Documents     Music             ssh_commands.txt  workspaces
gabe@gabe-XPS-13-9300:~$ cd websites/
```

Then, clone (copy the source code) into your decided porjected folder by copying and pasting the follow command into the command line.

```bash
git clone INSERT_LINK
```

You must now download VSCode to be able to edit the source code. Once you can downlaoded VSCode, you should be able to open the source code using the following command in the command line. 

```bash
code curator-website
```

### Project Structure

Here is the project structure
- `index.html`: the homepage of your website. Should remain the same (minimal editing)
- `curation.html`: a page for your events and stuff. Should be regularly updated
- `writing.html`: a page to list all of the writing you've done
- `assets/style.css`: defining code for the look and style of the website
- `articles`: a folder for individual articles that you can add as you go
- `images`: a folder for images you want for your website (every page can find them)


`python3 -m http.server 8000`
