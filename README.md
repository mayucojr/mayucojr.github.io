# Mario's Personal Website

cd m tab before you do anything 
### Adding an article

1. Open VSCode and open the folder called `mayucojr.github.io`
2. Create a new markdown file at `assets/articles/markdown` named `DayMonthYear.md`
3. Create a new folder at `assets/images` named `article_DayMonthYear`
4. Add relevant media in this new image folder
5. Copy and paste the format from previous articles into `DayMonthYear.md`
6. Write into the `.md` file
7. Once done, run the following command in the VSCode terminal (this builds the page from the `.md` file):
```bash
python3 scripts/build.py
```
8. If you would like, you can check your edits by hosting the website locally, by running:
```bash
python3 -m http.server 8000 --bind 127.0.0.1
```
9. Now, we can publish the changes to the website by pushing to GitHub, using the following commands (one at a time):
```bash
git add .
git commit -m 'adding new article'
git push origin master
```

### Adding a curation entry

1. Open VSCode and open the folder called `mayucojr.github.io`
2. Create a new markdown file at `assets/curation/markdown` named `DayMonthYear.md`
3. Create a new folder at `assets/images` named `curation_DayMonthYear`
4. Add relevant media in this new image folder
5. Copy and paste the format from previous curation entries into `DayMonthYear.md`
6. Write into the `.md` file
7. Once done, run the following command in the VSCode terminal (this builds the page from the `.md` file):
```bash
python3 scripts/build.py
```
8. If you would like, you can check your edits by hosting the website locally, by running:
```bash
python3 -m http.server 8000 --bind 127.0.0.1
```
9. Now, we can publish the changes to the website by pushing to GitHub, using the following commands (one at a time):

First, make sure your terminal is in the mayucojr.github.io folder, then run
```bash
git add .
```
```bash
git commit -m 'adding new curation entry'
```
```bash
git push origin master
```

### Project Structure

Here is the project structure:
- `curation.html`: a page for your curation entries
- `index.html`: the homepage of your website
- `writing.html`: a page to list all of the writing you've done
- `contact.html`: a page so people know how to contact you
- `articles`: a folder for individual articles that you can add as you go
- `curation`: a folder for curation entries that you can add as you go
- `images`: a folder for images you want for your website (every page can find them)
- `assets/css/style.css`: defining code for the look and style of the website
- `assets/js/menu.js`: defines the menu action for the sidebar
- `scripts/build.py`: generates the html files from md files and updates writing.html and curation.html
