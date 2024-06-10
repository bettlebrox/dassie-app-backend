SELECT _id, _title, _summary, _created_at, _updated_at, _logged_at, _image, _source_navlog, _tab_id, _token_count, _document_id, _parent_document_id, left(_url,200),_text 
FROM public.article
ORDER BY _token_count DESC LIMIT 100
