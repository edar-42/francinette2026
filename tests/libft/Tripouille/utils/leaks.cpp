#include "leaks.hpp"

std::vector<ptr> mallocList;

#ifdef __unix__
// dlsym can call malloc itself (recent glibc): looking up malloc with it from malloc never ends (SIGSEGV).
// glibc exports its own malloc and free under these names.
extern "C" void * __libc_malloc(size_t size);
extern "C" void __libc_free(void * p);
#endif

// The vector also allocates memory: these allocations are not the ones of the tested function
static bool inMallocList = false;

bool operator==(ptr const & p1, ptr const & p2)
{
    return (p1.p == p2.p);
}

#ifdef __APPLE__
void * malloc(size_t size)
#endif
#ifdef __unix__
void * malloc(size_t size) throw()
#endif
{
#ifdef __unix__
    void * p = __libc_malloc(size);
#else
    void *(*libc_malloc)(size_t) = (void *(*)(size_t))dlsym(RTLD_NEXT, "malloc");
    void * p = libc_malloc(size);
#endif
    if (!inMallocList)
        mallocListAdd(p, size);
    return (p);
}

#ifdef __APPLE__
void free(void * p)
#endif
#ifdef __unix__
void free(void * p) throw()
#endif
{
#ifdef __unix__
    __libc_free(p);
#else
    void (*libc_free)(void*) = (void (*)(void *))dlsym(RTLD_NEXT, "free");
    libc_free(p);
#endif
    if (!inMallocList)
        mallocListRemove(p);
}

void mallocListAdd(void * p, size_t size)
{
    inMallocList = true;
    mallocList.push_back(ptr(p, size));
    inMallocList = false;
}

void mallocListRemove(void * p)
{
    inMallocList = true;
    std::vector<ptr>::iterator it = find(mallocList.begin(), mallocList.end(), ptr(p));
    if (it != mallocList.end())
        mallocList.erase(it);
    inMallocList = false;
}

void showLeaks(void)
{
    if (mallocList.size() != 0)
    {
        std::ostringstream ss; ss << FG_RED << "LEAKS.KO "; write(1, ss.str().c_str(), ss.str().size());
        std::vector<ptr>::iterator it = mallocList.begin(); std::vector<ptr>::iterator ite = mallocList.end();
        for (; it != ite; ++it)
            {std::ostringstream ss; ss << "[" << it->p << " : " << it->size << "] "; write(1, ss.str().c_str(), ss.str().size());}
    }
    mallocList.clear();
}
