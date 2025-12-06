import { Link } from 'react-router-dom';

const kindleSteps = [
  'Mở trình duyệt trên Kindle và truy cập',
  'Trên điện thoại, mở ứng dụng quét mã QR/camera và quét mã QR hiển thị trên Kindle.',
  'Sau khi quét thành công, chọn cuốn sách muốn đọc trên điện thoại và xác nhận gửi tới Kindle.',
  'Quay lại Kindle, tải lại trang hoặc đợi vài giây để sách tự xuất hiện trong giao diện đơn giản.',
];

const phoneSteps = [
  'Đảm bảo điện thoại và Kindle cùng kết nối Internet ổn định.',
  'Nếu quét QR không thành công, giữ camera ổn định và tăng độ sáng màn hình Kindle.',
  'Khi sách đã gửi, có thể mở lại khosach.mnd.vn/kindle bất cứ lúc nào để tiếp tục.',
];

export function KindleGuidePage() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <main className="max-w-2xl mx-auto px-4 py-12">
        <p className="text-sm uppercase tracking-wide text-slate-500">Hướng dẫn</p>
        <h1 className="mt-2 text-3xl font-semibold">Đọc sách trên Kindle</h1>
        <p className="mt-4 text-lg leading-relaxed">
          Giao diện này giúp bạn mở kho sách nhanh chóng trên trình duyệt của Kindle và gửi sách trực tiếp từ
          điện thoại. Làm theo các bước bên dưới để bắt đầu.
        </p>

        <section className="mt-8 rounded-2xl bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-slate-800">Trên Kindle</h2>
          <ol className="mt-4 list-decimal space-y-3 pl-6 text-base leading-relaxed">
            {kindleSteps.map((step, index) => (
              <li key={step} className="pl-2">
                {step}
                {index === 0 && (
                  <>
                    {' '}
                    <a
                      href="https://khosach.mnd.vn"
                      className="text-blue-600 underline"
                      target="_blank"
                      rel="noreferrer"
                    >
                      khosach.mnd.vn
                    </a>
                    .
                  </>
                )}
              </li>
            ))}
          </ol>
        </section>

        <section className="mt-6 rounded-2xl border border-dashed border-slate-200 bg-slate-100/70 p-6">
          <h2 className="text-xl font-semibold text-slate-800">Trên điện thoại</h2>
          <ul className="mt-4 list-disc space-y-3 pl-6 text-base leading-relaxed">
            {phoneSteps.map((tip) => (
              <li key={tip} className="pl-2">
                {tip}
              </li>
            ))}
          </ul>
        </section>

        <div className="mt-10 flex flex-wrap gap-4">
          <Link
            to="/"
            className="inline-flex items-center justify-center rounded-full bg-slate-900 px-6 py-3 text-white transition hover:bg-slate-800"
          >
            Quay lại thư viện
          </Link>
          <a
            href="https://khosach.mnd.vn"
            className="inline-flex items-center justify-center rounded-full border border-slate-300 px-6 py-3 text-slate-700 transition hover:border-slate-400"
          >
            Mở khosach.mnd.vn
          </a>
        </div>
      </main>
    </div>
  );
}

