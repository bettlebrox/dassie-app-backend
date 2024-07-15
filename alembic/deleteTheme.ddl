delete from theme where "_id" = '20d2bc27-d38b-43e5-8a5b-a19b32644960'

WITH deleted as (delete from association where article_id in (SELECT article_id FROM "association" where theme_id = '20d2bc27-d38b-43e5-8a5b-a19b32644960') returning article_id)
delete from article where _id in (select * from deleted);

delete from recurrent where theme_id  = '20d2bc27-d38b-43e5-8a5b-a19b32644960';
delete from recurrent where related_id  = '20d2bc27-d38b-43e5-8a5b-a19b32644960';
delete from sporadic where theme_id  = '20d2bc27-d38b-43e5-8a5b-a19b32644960';