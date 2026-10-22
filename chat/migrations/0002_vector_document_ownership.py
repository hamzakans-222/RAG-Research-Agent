from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("chat", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="conversation",
            constraint=models.UniqueConstraint(
                fields=("id", "owner"), name="chat_conversation_owner_pair",
            ),
        ),
        migrations.RunSQL(
            sql="""
                CREATE EXTENSION IF NOT EXISTS vector;
                CREATE TABLE IF NOT EXISTS public.rag_documents (
                    langchain_id UUID PRIMARY KEY,
                    content TEXT NOT NULL,
                    embedding vector(768) NOT NULL,
                    langchain_metadata JSON
                );
                ALTER TABLE public.rag_documents
                    ADD COLUMN user_id INTEGER,
                    ADD COLUMN id_conversation UUID;
                ALTER TABLE public.rag_documents
                    ADD CONSTRAINT rag_documents_user_fk
                        FOREIGN KEY (user_id) REFERENCES auth_user (id)
                        ON DELETE CASCADE,
                    ADD CONSTRAINT rag_documents_conversation_owner_fk
                        FOREIGN KEY (id_conversation, user_id)
                        REFERENCES chat_conversation (id, owner_id)
                        MATCH FULL ON DELETE CASCADE;
                CREATE INDEX rag_documents_scope_idx
                    ON public.rag_documents (user_id, id_conversation);
            """,
            # Keep the document table and embeddings when rolling back.
            reverse_sql="""
                DROP INDEX public.rag_documents_scope_idx;
                ALTER TABLE public.rag_documents
                    DROP CONSTRAINT rag_documents_conversation_owner_fk,
                    DROP CONSTRAINT rag_documents_user_fk,
                    DROP COLUMN id_conversation,
                    DROP COLUMN user_id;
            """,
        ),
    ]
