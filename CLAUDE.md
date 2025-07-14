The package manager you use is uv -- python and packages will be run using uv run, dependencies will be managed using uv add/rm.

Reference documentation is found in respources.  

The ultimate goal of this project is to query an existing imessage database (w/in some daterange and optionally limited to a list of numbers/contacts) and store the messages in the imessage-db database and poll for new messages while running (and ingest all messages that have been received during downtime on startup w/o introducing duplicates into the database)

