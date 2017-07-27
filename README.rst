Email Archiver & Indexer
========================

Basic email archiver and indexer, intended to be used with Postfix.

Configuration
------------------
- Add the following options to Postfix's `main.cf`:

 - `always_bcc = archive@archive.example.com`
 - `archive_destination_recipient_limit = 1`

- Configure the domain `archive.example.com` to be a null-delivery domain using the `archive` transport (How to do this varies based on your local postfix configuration)
- Add an entry in Postfix's `master.cf` to enable delivery to the archiver script:

::

  archive    unix    -    n    n    -    -    pipe
    flags=D user=vmail:vmail argv=/path/to/email_archive -a

Change the user/group as appropriate for your configuration

