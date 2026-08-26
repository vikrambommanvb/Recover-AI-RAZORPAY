class MockCursor:
    def __init__(self, data):
        self.data = data
        self.index = 0
        
    def skip(self, n):
        self.data = self.data[n:]
        return self
        
    def limit(self, n):
        self.data = self.data[:n]
        return self

    def sort(self, key_or_list, direction=None):
        if isinstance(key_or_list, list):
            sort_key = key_or_list[0][0]
            reverse = key_or_list[0][1] == -1
        else:
            sort_key = key_or_list
            reverse = direction == -1
            
        def get_sort_val(x):
            val = x.get(sort_key)
            if val is None:
                return ""
            return val

        self.data.sort(key=get_sort_val, reverse=reverse)
        return self
        
    def __aiter__(self):
        return self
        
    async def __anext__(self):
        if self.index < len(self.data):
            res = self.data[self.index]
            self.index += 1
            return res
        else:
            raise StopAsyncIteration


class MockCollection:
    def __init__(self):
        self.docs = []
        
    def _matches_filter(self, doc, filter):
        for k, v in filter.items():
            # If the filter key represents a query operator or nested fields
            if k.startswith("$"):
                continue
                
            if "." in k:
                parts = k.split(".")
                val = doc
                for part in parts:
                    if isinstance(val, dict):
                        val = val.get(part)
                    else:
                        val = None
            else:
                val = doc.get(k)

            # Resolve enum values if any
            if hasattr(val, "value"):
                val = val.value

            if isinstance(v, dict):
                if "$in" in v:
                    # Resolve values in the list if they are enums
                    in_list = [x.value if hasattr(x, "value") else x for x in v["$in"]]
                    if val not in in_list:
                        return False
                elif "$lt" in v:
                    limit = v["$lt"].value if hasattr(v["$lt"], "value") else v["$lt"]
                    if val is None or val >= limit:
                        return False
                elif "$gt" in v:
                    limit = v["$gt"].value if hasattr(v["$gt"], "value") else v["$gt"]
                    if val is None or val <= limit:
                        return False
                else:
                    target_val = v
                    if val != target_val:
                        return False
            else:
                target_val = v.value if hasattr(v, "value") else v
                if val != target_val:
                    return False
        return True

    async def find_one(self, filter):
        for doc in self.docs:
            if self._matches_filter(doc, filter):
                return doc
        return None
        
    def find(self, filter=None):
        filter = filter or {}
        matched = []
        for doc in self.docs:
            if self._matches_filter(doc, filter):
                matched.append(doc)
        return MockCursor(matched)
        
    async def update_one(self, filter, update, upsert=False):
        doc = await self.find_one(filter)
        set_dict = update.get("$set", {})
        if doc:
            doc.update(set_dict)
        elif upsert:
            new_doc = {**filter, **set_dict}
            self.docs.append(new_doc)
        return None

    async def replace_one(self, filter, doc, upsert=True):
        existing = await self.find_one(filter)
        if existing:
            self.docs.remove(existing)
            self.docs.append(doc)
        elif upsert:
            self.docs.append(doc)
        return None
        
    async def insert_many(self, docs):
        self.docs.extend(docs)
        class InsertResult:
            inserted_ids = [doc.get("payment_id") for doc in docs]
        return InsertResult()

    async def insert_one(self, doc):
        self.docs.append(doc)
        return None

    async def update_many(self, filter, update):
        set_dict = update.get("$set", {})
        count = 0
        for doc in self.docs:
            if self._matches_filter(doc, filter):
                doc.update(set_dict)
                count += 1
        return count

    async def count_documents(self, filter):
        count = 0
        for doc in self.docs:
            if self._matches_filter(doc, filter):
                count += 1
        return count


class MockDatabase:
    def __init__(self):
        self.collections = {}
        
    def __getitem__(self, name):
        if name not in self.collections:
            self.collections[name] = MockCollection()
        return self.collections[name]
