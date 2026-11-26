using System;
using System.Diagnostics;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;

namespace DatalessonCertWpf
{
    public partial class MainWindow : Window
    {
        private static readonly Brush NeutralDotBrush = CreateFrozenBrush("#64708C");
        private static readonly Brush LoadingDotBrush = CreateFrozenBrush("#F6B93B");
        private static readonly Brush SuccessDotBrush = CreateFrozenBrush("#2ED573");
        private static readonly Brush ErrorDotBrush = CreateFrozenBrush("#FF6B6B");

        public MainWindow()
        {
            InitializeComponent();
        }

        private static Brush CreateFrozenBrush(string hex)
        {
            var brush = (SolidColorBrush)new BrushConverter().ConvertFromString(hex);
            brush.Freeze();
            return brush;
        }

        private void TitleBar_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
        {
            if (e.ButtonState == MouseButtonState.Pressed)
            {
                DragMove();
            }
        }

        private void Minimize_Click(object sender, RoutedEventArgs e)
        {
            WindowState = WindowState.Minimized;
        }

        private void Close_Click(object sender, RoutedEventArgs e)
        {
            Close();
        }

        private void UrlBox_TextChanged(object sender, TextChangedEventArgs e)
        {
            UrlPlaceholder.Visibility = string.IsNullOrEmpty(UrlBox.Text)
                ? Visibility.Visible
                : Visibility.Collapsed;
        }

        private void UrlBox_KeyDown(object sender, KeyEventArgs e)
        {
            if (e.Key == Key.Enter)
            {
                Resolve_Click(sender, e);
            }
        }

        private void Paste_Click(object sender, RoutedEventArgs e)
        {
            try
            {
                if (Clipboard.ContainsText())
                {
                    UrlBox.Text = Clipboard.GetText().Trim();
                    UrlBox.CaretIndex = UrlBox.Text.Length;
                }
            }
            catch (Exception)
            {
            }
        }

        private async void Resolve_Click(object sender, RoutedEventArgs e)
        {
            LessonTarget target;
            try
            {
                target = CertificateResolver.ParseLessonUrl(UrlBox.Text, SlugBox.Text);
            }
            catch (ArgumentException exc)
            {
                SetStatus(exc.Message, ErrorDotBrush);
                return;
            }

            SlugBox.Text = target.Slug;
            ResultBox.Text = string.Empty;
            ResolveButton.IsEnabled = false;
            ResolveButton.Content = "Проверяю...";
            CopyButton.IsEnabled = false;
            OpenButton.IsEnabled = false;
            SetStatus("Проверяю страницу сертификата на сервере...", LoadingDotBrush);

            try
            {
                CertificateResult result = await CertificateResolver.VerifyCertificateUrlAsync(target);
                ResultBox.Text = result.Url;
                CopyButton.IsEnabled = true;
                OpenButton.IsEnabled = true;
                SetStatus(string.Format("Готово. Урок: {0}. Можно открыть страницу и скачать сертификат.", result.Slug), SuccessDotBrush);
            }
            catch (InvalidOperationException exc)
            {
                SetStatus(exc.Message, ErrorDotBrush);
            }
            finally
            {
                ResolveButton.IsEnabled = true;
                ResolveButton.Content = "Получить сертификат";
            }
        }

        private void Copy_Click(object sender, RoutedEventArgs e)
        {
            if (string.IsNullOrEmpty(ResultBox.Text))
            {
                return;
            }

            Clipboard.SetText(ResultBox.Text);
            SetStatus("Ссылка скопирована в буфер обмена.", SuccessDotBrush);
        }

        private void Open_Click(object sender, RoutedEventArgs e)
        {
            if (string.IsNullOrEmpty(ResultBox.Text))
            {
                return;
            }

            Process.Start(new ProcessStartInfo(ResultBox.Text) { UseShellExecute = true });
        }

        private void SetStatus(string message, Brush dotBrush)
        {
            StatusText.Text = message;
            StatusDot.Fill = dotBrush ?? NeutralDotBrush;
        }
    }
}
