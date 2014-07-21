This directory contains some example manifest documents. Manifest documents are Yaml configuration files with the following structure:

---

days: X (The day(s) that the consumer should be run)
hour: X (The hour(s) the consumer should be run)
minute: X (The minute(s) the consumer should be run)

directory: X (The directory name that documents should be stored under)

name: X (The proper name of the service)

git-url: X (A link to the git repository for a consumer, so that it can be installed)

file-format: .X (The file format that the raw files will be saved as)

...
