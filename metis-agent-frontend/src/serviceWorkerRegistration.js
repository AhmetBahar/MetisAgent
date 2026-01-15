// Bu kod parçası, bir uygulamanın hizmet çalışanının kayıt edilip edilmeyeceğini kontrol eder.
// Yerel geliştirme sırasında hizmet çalışanının nasıl çalıştığını daha iyi anlamak isterseniz,
// https://cra.link/PWA adresini ziyaret edin.

const isLocalhost = Boolean(
    window.location.hostname === 'localhost' ||
      // [::1] localhost'un IPv6 adresidir.
      window.location.hostname === '[::1]' ||
      // 127.0.0.0/8, localhost için ayrılmış IPv4 adresleridir.
      window.location.hostname.match(/^127(?:\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)){3}$/)
  );
  
  export function register(config) {
    if (process.env.NODE_ENV === 'production' && 'serviceWorker' in navigator) {
      // URL constructor, kodu parça parça oluşturmak için bir yoldur.
      const publicUrl = new URL(process.env.PUBLIC_URL, window.location.href);
      if (publicUrl.origin !== window.location.origin) {
        // PUBLIC_URL, sayfamızın sunulduğu kaynakla aynı kaynakta değilse,
        // hizmet çalışanı çalışmaz. Bu, CDN kullanılırken olabilir.
        // https://github.com/facebook/create-react-app/issues/2374 adresine bakın
        return;
      }
  
      window.addEventListener('load', () => {
        const swUrl = `${process.env.PUBLIC_URL}/service-worker.js`;
  
        if (isLocalhost) {
          // Bu localhost'ta çalışıyor. Service worker'ın hala var olup olmadığını kontrol edelim.
          checkValidServiceWorker(swUrl, config);
  
          // Add some additional logging to localhost, pointing developers to the
          // service worker/PWA documentation.
          navigator.serviceWorker.ready.then(() => {
            console.log(
              'Bu uygulama önce önbelleğe alınmış içerikle sunuluyor, ' +
                'daha fazla bilgi için buraya bakın: https://cra.link/PWA'
            );
          });
        } else {
          // Localhost değil. Sadece service worker'ı kaydet
          registerValidSW(swUrl, config);
        }
      });
    }
  }
  
  function registerValidSW(swUrl, config) {
    navigator.serviceWorker
      .register(swUrl)
      .then((registration) => {
        registration.onupdatefound = () => {
          const installingWorker = registration.installing;
          if (installingWorker == null) {
            return;
          }
          installingWorker.onstatechange = () => {
            if (installingWorker.state === 'installed') {
              if (navigator.serviceWorker.controller) {
                // Bu noktada, eski içerik önbellekten temizlenecek,
                // ve yeni içerik tarayıcıya hizmet edecek.
                console.log(
                  'Yeni içerik indirmek için mevcut. ' +
                    'Sayfayı yenilediğinizde bu içerik yüklenecektir.'
                );
  
                // İsteğe bağlı bir callback çalıştırma
                if (config && config.onUpdate) {
                  config.onUpdate(registration);
                }
              } else {
                // Bu noktada, her şey önbelleğe alındı.
                // "İçerik çevrimdışı kullanım için önbelleğe alındı." mesajını göstermek için idealdir.
                console.log('İçerik çevrimdışı kullanım için önbelleğe alındı.');
  
                // İsteğe bağlı bir callback çalıştırma
                if (config && config.onSuccess) {
                  config.onSuccess(registration);
                }
              }
            }
          };
        };
      })
      .catch((error) => {
        console.error('Service worker kaydı sırasında hata:', error);
      });
  }
  
  function checkValidServiceWorker(swUrl, config) {
    // Service worker'ın bulunup bulunamadığını kontrol edin. 404 durumunda, uygulama yeniden yüklenebilir.
    fetch(swUrl, {
      headers: { 'Service-Worker': 'script' },
    })
      .then((response) => {
        // Service worker mevcut ve JS dosyası olarak geliyor mu kontrol edin.
        const contentType = response.headers.get('content-type');
        if (
          response.status === 404 ||
          (contentType != null && contentType.indexOf('javascript') === -1)
        ) {
          // Service worker bulunamadı. Muhtemelen başka bir uygulama. Sayfayı yenileyin.
          navigator.serviceWorker.ready.then((registration) => {
            registration.unregister().then(() => {
              window.location.reload();
            });
          });
        } else {
          // Service worker bulundu. Normal şekilde devam edin.
          registerValidSW(swUrl, config);
        }
      })
      .catch(() => {
        console.log('İnternet bağlantısı yok. Uygulama çevrimdışı modda çalışıyor.');
      });
  }
  
  export function unregister() {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.ready
        .then((registration) => {
          registration.unregister();
        })
        .catch((error) => {
          console.error(error.message);
        });
    }
  }